import os
import logging
import redis
import time
from dataclasses import dataclass

from .ies_utils import session_maker, TripsIES, IES_JOB_STATUS_MAPPING, AGVMsg, MsgToIES
from plugins.plugin_comms import send_req_to_FM
from models.trip_models import TripStatus

logger = logging.getLogger("plugin_ies")


class AGV_ACTIVITY:
    unsupported = 0
    idle = 1
    driving = 2
    loading = 3
    unloading = 4
    charging = 5
    maintenance = 6


def send_msg(msg):
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
        send_msg(agv_update_msg)
    return


# read status from periodic messages, for those trips in DB, send periodic msgs to IES.
def send_job_updates():
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
                    next_idx_aug, msg_to_ies = _process_trip_details(trip, trip_details)

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
                            send_msg(assigned_msg_to_ies)

                        send_msg(msg_to_ies)  # IS THIS NECESSARY?
                        trip.status = trip_status
                    elif trip.status == TripStatus.EN_ROUTE:
                        logger.info(
                            f"Trip status: {trip.status}, sending continuous updates!"
                        )
                        send_msg(msg_to_ies)  # CAN THIS MOVE OUTSIDE THE LOOP?

            db_session.commit()
            db_session.close()

        time.sleep(30)


def _process_trip_details(trip, trip_details):
    trip_status = trip_details["trip_details"]["status"]
    next_idx_aug = trip_details["trip_details"]["next_idx_aug"]
    if next_idx_aug == 0:
        next_idx_aug = None
    if trip_status == TripStatus.SUCCEEDED:
        next_idx_aug = 0
    lastCompletedTask = _get_last_completed_task(trip.actions, trip.locations, next_idx_aug)
    msg_to_ies = _get_msg_to_ies(
        trip.externalReferenceId, IES_JOB_STATUS_MAPPING[trip_status], lastCompletedTask
    )
    logger.debug(f"DB status: {trip.status}")
    logger.debug(f"FM Req status: {trip_status}")
    return next_idx_aug, msg_to_ies


def _get_last_completed_task(trip_actions, trip_locations, next_idx_aug):
    return {
        "ActionName": trip_actions[next_idx_aug - 1] if next_idx_aug is not None else "",
        "LocationId": trip_locations[next_idx_aug - 1] if next_idx_aug is not None else "",
    }


def _get_msg_to_ies(ref_id, trip_status, last_task):
    msg_to_ies = MsgToIES("JobUpdate", ref_id, trip_status)
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
