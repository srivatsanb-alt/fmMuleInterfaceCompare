import os
import logging
import redis
import aioredis
import time
import json
import ast
from dataclasses import dataclass

from .ies_utils import (
    session_maker,
    TripsIES,
    IES_JOB_STATUS_MAPPING,
    AGVMsg,
    MsgToIES,
    get_fleet_status_msg,
    read_dict_var_from_redis_db,
    get_ati_station_details,
    remove_from_pending_jobs_db,
    session,
    get_end_station
)
from plugins.plugin_comms import send_req_to_FM
from models.trip_models import TripStatus
from models.db_session import DBSession

logger = logging.getLogger("plugin_ies")
redis_db = redis.from_url(os.getenv("FM_REDIS_URI"), decode_responses=True)


class AGV_ACTIVITY:
    unsupported = 0
    idle = 1
    driving = 2
    loading = 3
    unloading = 4
    charging = 5
    maintenance = 6


def send_msg_to_ies(msg):
    pub = redis.from_url(os.getenv("FM_REDIS_URI"), decode_responses=True)
    pub.publish("channel:plugin_ies", str(msg))


def send_agv_update_and_fault(sherpa_name, externalReferenceId):
    if sherpa_name is None:
        return
    status_code, sherpa_summary = send_req_to_FM(
        "ies", "sherpa_summary", req_type="get", query=sherpa_name
    )
    if status_code == 200:
        agv_update_msg = AGVMsg(
            "AgvFault", externalReferenceId, sherpa_summary["sherpa"]["hwid"], "ati-sherpa"
        ).to_dict()
        if sherpa_summary["sherpa_status"]["mode"] == "error":
            agv_update_msg.update({"errorMessage": "ati-sherpa in error"})
        else:
            sherpa_status = _get_sherpa_status(sherpa_summary, externalReferenceId)
            agv_update_msg.update(sherpa_status)
        send_msg_to_ies(agv_update_msg)
    return


async def check_status_and_combine_trips():
    redis_conn = aioredis.Redis.from_url(
        os.getenv("FM_REDIS_URI"), max_connections=10, decode_responses=True
    )
    psub = redis_conn.pubsub()
    await psub.subscribe("channel:status_updates")
    while True:
        fleet_status = await psub.get_message(ignore_subscribe_messages=True, timeout=5)
        if fleet_status:
            fleet_status_data = ast.literal_eval(fleet_status["data"])
            maybe_combine_and_book_trips(fleet_status_data)


# read status from periodic messages, for those trips in DB, send periodic msgs to IES.
def send_job_updates():
    logger.info("running send_job_updates")
    while True:
        with session_maker() as db_session:
            all_active_trips = _get_active_trips(db_session)
            for trip in all_active_trips:
                status_code, trip_status_response = _get_trip_status_response(trip)
                for trip_id, trip_details in trip_status_response.items():
                    send_agv_update_and_fault(
                        trip_details["sherpa_name"], trip.externalReferenceId
                    )
                    trip_status = trip_details["trip_details"]["status"]
                    _, msg_to_ies = _process_trip_details(trip, trip_details)

                    if trip.status != trip_status:  # WHAT IS THIS CHECK
                        logger.info(
                            f"trip_id: {trip_id}, FM_response_status: {trip_status}, db_status: {trip.status}"
                        )
                        if (
                            trip.status == TripStatus.BOOKED
                            and trip_status == TripStatus.EN_ROUTE
                        ):
                            # Need to mandatorily send succeeded message to IES
                            assigned_msg_to_ies = _get_msg_to_ies(
                                trip.externalReferenceId,
                                IES_JOB_STATUS_MAPPING[TripStatus.ASSIGNED],
                                msg_to_ies["lastCompletedTask"],
                            )
                            logger.info("Sending SCHEDULED msg to IES.")
                            send_msg_to_ies(assigned_msg_to_ies)
                        trip.status = trip_status
                        send_msg_to_ies(msg_to_ies)
                    elif trip.status == TripStatus.EN_ROUTE:
                        logger.info(
                            f"Trip status: {trip.status}, sending continuous updates!"
                        )
                        send_msg_to_ies(msg_to_ies)  # periodic message

            db_session.commit()
            db_session.close()

        time.sleep(30)


def maybe_combine_and_book_trips(fleet_data):
    logger.info(f"fleet_data: {fleet_data}")
    if "sherpa_status" in fleet_data.keys():
        for sherpa in fleet_data["sherpa_status"]:
            sherpa_status = fleet_data["sherpa_status"][sherpa]["idle"]
            logger.info(f"Sherpa status: {sherpa_status}, sherpa: {sherpa}")
            if sherpa_status is True:
                combine_and_book_trip()
                break
    return


def combine_and_book_trip():
    pending_trips = read_dict_var_from_redis_db(redis_db, "pending_jobs")
    logger.info(f"pending_trips: {pending_trips}")
    dest_stations_data = []
    try:
        logger.info(f"pending_trip ids: {list(pending_trips.keys())[:36]}")  # MAKE IT A CONFIG
    except Exception as e:
        logger.info(f"error: {e}")
    for ref_id in list(pending_trips.keys()):
        dest_stations_data.append([
            get_ati_station_details(task["LocationId"])
            for task in pending_trips[ref_id]["taskList"]])
    logger.info(f"before flatten: {dest_stations_data}")
    dest_stations_data = _flatten_list(dest_stations_data)
    stations_ranks = [item[1] for item in dest_stations_data]
    stations_names = [item[0] for item in dest_stations_data]
    logger.info(f"after flatten: {dest_stations_data}")
    booked_trips_ids = list(pending_trips.keys())
    logger.info(f"booked_trip_ids: {booked_trips_ids}")
    sorted_ranks = sorted(stations_ranks)
    sorted_inds = [stations_ranks.index(k) for k in sorted_ranks]
    logger.info(f"sorted_inds: {sorted_inds}")
    sorted_stations_names = [stations_names[k] for k in sorted_inds]
    sorted_stations_names = _remove_duplicates(sorted_stations_names)
    logger.info(f"sorted_stations_names: {sorted_stations_names}")
    if sorted_stations_names:
        end_station = get_end_station("ECFA")
        logger.info(f"end station after combining: {end_station}")
        sorted_stations_names.append(end_station)
        logger.info(f"sorted stations: {sorted_stations_names}")
        req_json = {"trips": [{"route": sorted_stations_names, "priority": 1}]}
        logger.info(f"sending booking req to fm: {req_json}")
        status_code, trip_booking_response = send_req_to_FM(
            "ies", "trip_book", req_type="post", req_json=req_json
        )
        if trip_booking_response is not None:
            logger.info(f"trip_booking_response:{trip_booking_response}")
            for trip_id, trip_details in trip_booking_response.items():
                trip = TripsIES(
                    trip_id=trip_id,
                    booking_id=trip_details["booking_id"],
                    externalReferenceId=booked_trips_ids[0],
                    status=trip_details["status"],
                    actions="",
                    locations=sorted_stations_names,
                )
                logger.info("adding combined trip to DB")
                session.add(trip)
                session.commit()
            for trip_id in booked_trips_ids:
                remove_from_pending_jobs_db(redis_db, trip_id)
        else:
            for trip_id in booked_trips_ids:
                msg_to_ies = _get_msg_to_ies(trip_id, "CANCELLED", None)
                msg_to_ies.update({"errorMessage": f"unable to combine trips for {trip_id}"})
                logger.info(f"req to FM failed, response code: {status_code}")
                send_msg_to_ies(msg_to_ies)
        return


def _process_trip_details(trip, trip_details):
    trip_status = trip_details["trip_details"]["status"]
    next_idx_aug = trip_details["trip_details"]["next_idx_aug"]
    if next_idx_aug == 0:
        next_idx_aug = None
    if trip_status == TripStatus.SUCCEEDED:
        next_idx_aug = 0
    lastCompletedTask = _get_last_completed_task(trip.actions, trip.locations, next_idx_aug)
    msg_to_ies = MsgToIES(
        "JobUpdate", trip.externalReferenceId, IES_JOB_STATUS_MAPPING[trip_status]
    ).to_dict()
    msg_to_ies.update({"lastCompletedTask": lastCompletedTask})
    logger.debug(f"DB status: {trip.status}")
    logger.debug(f"FM Req status: {trip_status}")
    return next_idx_aug, msg_to_ies


def _get_last_completed_task(trip_actions, trip_locations, next_idx_aug):
    logger.info(f"next_idx_aug: {next_idx_aug}")
    return {
        # "ActionName": trip_actions[next_idx_aug - 1] if next_idx_aug is not None else "",
        "ActionName": "",
        "LocationId": trip_locations[next_idx_aug - 1] if next_idx_aug is not None else "",
    }


def _get_msg_to_ies(ref_id, trip_status, last_task):
    msg_to_ies = MsgToIES("JobUpdate", ref_id, trip_status).to_dict()
    msg_to_ies.update({"lastCompletedTask": last_task})
    return msg_to_ies


def _get_trip_status_response(trip):
    # send_trip status req to FM using trip ID
    req_json = {"trip_ids": [trip.trip_id]}
    status_code, trip_status_response = send_req_to_FM(
        "ies", "trip_status", req_type="post", req_json=req_json
    )
    if trip_status_response is None:
        trip_status_response = {}
    return status_code, trip_status_response


def _get_active_trips(db_session):
    return (
        db_session.query(TripsIES)
        .filter(TripsIES.status != TripStatus.CANCELLED)
        .filter(TripsIES.status != TripStatus.SUCCEEDED)
        .filter(TripsIES.status != TripStatus.FAILED)
        .all()
    )


def _get_sherpa_status(sherpa_summary, externalReferenceId):
    map_position = {
        "mapName": sherpa_summary["fleet_name"],
        "positionX": sherpa_summary["sherpa_status"]["pose"][0],
        "positionY": sherpa_summary["sherpa_status"]["pose"][1],
        "positionZ": 0,
        "orientation": sherpa_summary["sherpa_status"]["pose"][2],
    }
    mule_position = {"logitude": 0, "latitude": 0, "elevation": 0, "orientation": 0}
    return {
        "messageType": "AgvUpdate",
        "vehicleId": sherpa_summary["sherpa"]["hwid"],
        "vehicleTypeID": "ati-sherpa",
        "availability": sherpa_summary["sherpa_status"]["inducted"],
        "currentJobId": externalReferenceId,
        "currentActivity": AGV_ACTIVITY.driving,
        "nextActivity": AGV_ACTIVITY.unsupported,
        "mapPostion": map_position,
        "geoPosition": mule_position,
        "speed": 1.0,
        "batteryLevel": None
        if sherpa_summary["sherpa_status"]["batteryLevel"] == -1
        else sherpa_summary["sherpa_status"]["batteryLevel"],
    }


def get_fleets_status_info():
    fleets_status = {}
    with DBSession() as db_session:
        fleets = db_session.get_all_fleets()
    for fleet in fleets:
        fleets_status[fleet] = get_fleet_status_msg(db_session, fleet)
    return fleets_status


def _flatten_list(ip_list):
    return [item for sublist in ip_list for item in sublist]


def _remove_duplicates(list):
    return [val for idx, val in enumerate(list) if idx == 0 or val != list[idx-1]]


def _add_end_station(route, end_station):
    return route.append(end_station)
