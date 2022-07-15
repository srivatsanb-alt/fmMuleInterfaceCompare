import requests
import json
import urls as urls
import os
from hivemind.core.db import get_db_session
import asyncio
import aioredis
import time

import client_models
from client_models import *

from hivemind.fleet_manager.logs import get_logger

from hivemind.fleet_manager.workers import enqueue


from hivemind.fleet_manager.entities import MuleActions
from hivemind.fleet_manager.constanst import MULE_TASK_MAP


#incomming messages
class IESMessages:
    #messages from IES to FM
    job_query = "JobQuery"
    job_create = "JobCreate"
    job_update = "JobUpdate"
    job_cancel = "JobCance"
    job_cancel_response = "JobCancelResponse"

    #messages from FM to IES
    agv_fault = "AgvFault"
    agv_update = "AgvUpdate"


task_activity_map = {
    MuleActions.DROP : ["unloading", 0],
    MuleActions.DRIVING: ["driving", 2],
    MuleActions.PICKUP: ["loading", 3],
    MuleActions.RECHARGE: ["charging", 5],
    MuleActions.PARK: ["idle", 1]
}


def handle_ies_job_create(msg):
    routes = []
    actions = []

    session = get_db_session()
    for trip in msg["taskList"]:
        result = session.query(client_models.BoschIESEntities).filter_by(client_models.external_id == trip["locationID"]).one()
        routes.append(result.entity_name)
        if trip["actionName"] == "Delivery":
            task = MULE_TASK_MAP[MuleActions.DROP]
        elif trip["actionName"] == "Pickup":
            task = MULE_TASK_MAP[MuleActions.PICKUP]
        elif trip["actionName"] == "Charging":
            task = MULE_TASK_MAP[MuleActions.RECHARGE]
        else:
            task = MULE_TASK_MAP[MuleActions.PARK]
        actions.append(task)

    msg_to_FM = {
        "routes": routes,
        "priority": msg["priority"],
        "actions": actions,
    }
    book_status = "REJECTED"
    response = requests.post(urls.book_trip, json = msg_to_FM)
    response_valid, response_json = check_if_response_valid(response)

    if response_valid and response_json.get("booked", None):
        book_status = "ACCEPTED"
        session = get_db_session()
        new_trip = BoschIESTrips(trid_id = response_json["trid_id"], external_id = msg["externalReferenceId"])
        session.add(new_trip)
        session.commit()

    msg_to_IES = {
        "messageType" : IESMessages.job_create,
        "externalReferenceId": msg["externalReferenceId"],
        "jobStatus": book_status
    }

    send_to_generic_channel(msg_to_IES, "channel:external_ies")


def handle_ies_job_cancel(msg):
    session = get_db_session()
    result = session.query(client_models.BoschIESTrips).filter_by(client_models.external_id == msg["externalReferenceId"]).one()
    current_trip_id = result.trip_id
    msg_to_FM = {
        "trip_id": current_trip_id,
        "metadata": {}
    }
    response = requests.post(urls.cancel_trip, json = msg_to_FM)
    response_valid, response_json = check_if_response_valid(response)

    msg_to_IES = {
        "messageType": "JobCancelResponse",
        "externalReferenceId": msg["externalReferenceId"],
        "jobStatus": " CANCELLED",
        }

    if not response_json.get("deleted", False):
        msg_to_IES.update({"errorCode": response.status_code})
        msg_to_IES.update({"errorMessage": response_json.get("error", "unknown")})
    else:
        session.query(client_models.BoschIESTrips).filter_by(client_models.external_id == msg["externalReferenceId"]).delete()
        session.commit()
    send_to_generic_channel(msg_to_IES, "channel:external_ies")


def handle_ies_job_update(msg):

    session = get_db_session()
    result = session.query(client_models.BoschIESTrips).filter_by(client_models.trid_id == msg["trip_id"]).one()
    externalReferenceId = result.external_id

    last_dest = msg["trip_details"]["routes"][-1]
    last_task = msg["trip_details"]["actions"][-1]

    if last_task == MuleActions.DROP:
        last_task = "Delivery"
    elif last_task == MuleActions.PICKUP:
        last_task = "Pickup"
    else:
        last_task = "Idle"

    status = msg["status"]
    if status in ["BOOKED", "ASSIGNED", "ENROUTE", "WAITING_STATION"]:
        status = "IN_PROGRESS"
    elif status in ["CANCELLED", "FAILED"]:
        pass
    elif status == "SUCCESS":
        status = "COMPLETED"

    msg_to_IES = {
        "messageType": "JobUpdate",
        "externalReferenceId": externalReferenceId,
        "lastCompletedTask": {
            "actionName": last_task,
            "locationId": last_dest
            },
        "jobStatus": status,
    }

    send_to_generic_channel(msg_to_IES, "channel:external_ies")

def handle_ies_agv_update(msg):
    current_task = msg["current_task"]
    next_task = msg["next_task"]

    session = get_db_session()
    result = session.query(client_models.BoschIESEntities).filter_by(client_models.entity_name == msg["sherpa_name"]).one()
    vehicleId = result.external_id
    vehicletype = result.entity_type

    result = session.query(client_models.BoschIESTrips).filter_by(client_models.trid_id == msg["trip_id"]).one()
    externalReferenceId = result.external_id

    # unsupported send 0
    current_activity = task_activity_map.get(current_task, ["unsupported",0])[1]
    next_activity = task_activity_map.get(next_task, ["unsupported",0])[1]

    msg_to_IES = {
        "messageType": "AgvUpdate",
        "vehicleId": vehicleId ,
        "vehicleTypeID":  vehicletype,
        "availability": "true",
        "currentJobId" : externalReferenceId,
        "currentActivity": current_activity,
        "nextActivity": next_activity,
        "mapPostion": {
                       "mapName": result.map,
                       "positionX": msg["pose"][0],
                       "positionY": msg["pose"][1],
                       "positionZ": 0,
                       "orientation": msg["pose"][2]
                       },
        "geoPosition": {
                    "logitude": 0,
                    "latitude": 0,
                    "elevation": 0,
                    "orientation": 0,
                    },
        "speed": msg["sherpa_velocity"],
        "batteryLevel": msg["shera_battery"] ,
    }
    send_to_generic_channel(msg_to_IES, "channel:external_ies")


def handle_ies_job_query(msg):
    start_time = msg["since"]
    end_time = msg["until"]

    session = get_db_session()
    results = session.query(client_models.BoschIESTrips).filter_by(client_models.id > 0).all()
    trip_ids = []

    for result in results:
        trip_ids.append(result.trip_id)

    msg_to_FM = {
	   "trip_ids": trip_ids,
	   "booked_from": start_time,
	   "booked_to": end_time,
    }

    response = requests.post(urls.trip_status, json = msg_to_FM)
    response_valid, response_json = check_if_response_valid(response)

    if response_valid:
        for trip in response_json.values():
            handle_ies_job_update(trip)


def handle_ies_msgs(msg):
    #messages from FM
    if msg["name"] == "FM":
        if msg["type"] == "trip_status":
            handle_ies_job_update(msg)
        elif msg["type"] == "sherpa_status":
            handle_ies_agv_update(msg)
        else:
            get_logger().info(f"Not a valid msg type {msg}")
        return

    #messages from IES
    if not msg["messageType"]:
        raise ValueError("messgaeType missing in IES message")

    msg_type = msg["messageType"]
    if msg_type == IESMessages.job_create:
        handle_ies_job_create(msg)
    elif msg_type == IESMessages.job_cancel:
        handle_ies_job_cancel(msg)
    elif msg_type == IESMessages.job_query:
        handle_ies_job_query(msg)
    else:
        get_logger().info(f"Not a valid msg type {msg}")


def send_to_generic_channel(msg, channel):
    pub = aioredis.Redis.from_url(os.getenv("HIVEMIND_REDIS_URI"), decode_responses = True)
    asyncio.run(pub.publish(channel, str(msg)))


def check_if_response_valid(response):
    response_valid = False
    response_json = {}
    if response.status_code == 200:
        response_valid = True
        response_json = response.json()

    return response_valid, response_json
