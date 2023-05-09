import datetime
import os
import logging
import redis
import aioredis
import time
import ast
from dataclasses import dataclass

from plugins.plugin_comms import send_req_to_FM
from models.trip_models import TripStatus
from models.db_session import DBSession
import plugins.ies.ies_utils as iu
import plugins.ies.ies_models as im

logger = logging.getLogger("plugin_ies")


class AGV_ACTIVITY:
    unsupported = 0
    idle = 1
    driving = 2
    loading = 3
    unloading = 4
    charging = 5
    maintenance = 6


def send_agv_update_and_fault(sherpa_name, externalReferenceId):
    if sherpa_name is None:
        return
    status_code, sherpa_summary = send_req_to_FM(
        "ies", "sherpa_summary", req_type="get", query=sherpa_name
    )
    if status_code == 200:
        agv_update_msg = iu.AGVMsg(
            "AgvFault", externalReferenceId, sherpa_summary["sherpa"]["hwid"], "ati-sherpa"
        ).to_dict()
        if sherpa_summary["sherpa_status"]["mode"] == "error":
            agv_update_msg.update({"errorMessage": "ati-sherpa in error"})
        else:
            sherpa_status = _get_sherpa_status(sherpa_summary, externalReferenceId)
            agv_update_msg.update(sherpa_status)
        iu.send_msg_to_ies(agv_update_msg)
    return


def delete_old_data_from_db(dbsession):
    ies_info = dbsession.session.query(im.IESInfo).first()
    backup_days = ies_info.backup_days
    dt = datetime.datetime.now() + datetime.timedelta(days=-backup_days)
    dbsession.delete_old_bookings_and_combined_trips(dt)


# read status from periodic messages, for those trips in DB, send periodic msgs to IES.
def send_job_updates():
    while True:
        with im.DBSession() as dbsession:
            delete_old_data_from_db(dbsession)
            all_active_combined_trips = dbsession.get_ongoing_combined_trips()
            status_code, trip_status_response = _get_trip_status_response(
                all_active_combined_trips
            )
            if status_code != 200:
                logger.info(f"trip status req to FM failed")
                continue

            for combined_trip in all_active_combined_trips:
                trip_id = combined_trip.trip_id
                trip_details = trip_status_response.get(str(trip_id))
                # send_agv_update_and_fault(trip_details["sherpa_name"], trip.ext_ref_id)

                trip_status_from_FM = trip_details["trip_details"]["status"]
                next_idx_aug_from_FM = trip_details["trip_details"]["next_idx_aug"]
                trip_status_db = combined_trip.status
                next_idx_aug_db = combined_trip.next_idx_aug
                logger.info(
                    f"Trip id {trip_id}; FM: {trip_status_from_FM, next_idx_aug_from_FM}; DB: {trip_status_db, next_idx_aug_db}"
                )
                if (
                    trip_status_from_FM != trip_status_db
                    or next_idx_aug_from_FM != next_idx_aug_db
                ):
                    _send_JobUpdate_msgs(
                        combined_trip,
                        trip_status_from_FM,
                        next_idx_aug_from_FM,
                        dbsession,
                    )
                    combined_trip.status = trip_status_from_FM
                    combined_trip.next_idx_aug = next_idx_aug_from_FM
        time.sleep(10)


def _send_JobUpdate_msgs(
    combined_trip, trip_status_from_FM, next_idx_aug_from_FM, dbsession
):
    if next_idx_aug_from_FM == None:
        next_idx_aug_from_FM = 0
    route = combined_trip.combined_route
    last_completed_task = (
        None if next_idx_aug_from_FM == 0 else route[next_idx_aug_from_FM - 1]
    )
    lastCompletedTaskMsg = iu.get_last_completed_task_msg(last_completed_task)
    # send messages for all ext_ref_ids with approproate status
    active_booking_reqs = dbsession.get_active_booking_reqs_for_combined_trip(combined_trip)
    for booking_req in active_booking_reqs:
        ext_ref_id = booking_req.ext_ref_id
        completed_route = route[0:next_idx_aug_from_FM]
        if (
            set(completed_route).intersection(set(booking_req.route))
            != set(booking_req.route)
            or len(combined_trip.trips) == 1
        ):
            msg_to_ies = iu.MsgToIES(
                "JobUpdate", ext_ref_id, iu.IES_JOB_STATUS_MAPPING[trip_status_from_FM]
            ).to_dict()
            msg_to_ies.update({"lastCompletedTask": lastCompletedTaskMsg})
            booking_req.status = trip_status_from_FM
        else:
            msg_to_ies = iu.MsgToIES(
                "JobUpdate", ext_ref_id, iu.IES_JOB_STATUS_MAPPING[TripStatus.SUCCEEDED]
            ).to_dict()
            booking_req.status = TripStatus.SUCCEEDED
        iu.send_msg_to_ies(msg_to_ies)

    return


def _get_trip_status_response(combined_trips):
    # send_trip status req to FM using trip IDs
    trip_ids = []
    for combined_trip in combined_trips:
        trip_ids.append(combined_trip.trip_id)
    req_json = {"trip_ids": trip_ids}
    status_code, trip_status_response = send_req_to_FM(
        "ies", "trip_status", req_type="post", req_json=req_json
    )
    if trip_status_response is None:
        trip_status_response = {}
    return status_code, trip_status_response


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
