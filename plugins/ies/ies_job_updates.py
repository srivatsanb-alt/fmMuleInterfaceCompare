import os
import logging
import redis
import time

from .ies_utils import session_maker, TripsIES
from plugins.plugin_comms import send_req_to_FM
from models.trip_models import TripStatus

IES_JOB_STATUS_MAPPING = {
    TripStatus.BOOKED: "ACCEPTED",
    TripStatus.ASSIGNED: "SCHEDULED",
    TripStatus.EN_ROUTE: "IN_PROGRESS",
    TripStatus.WAITING_STATION: "IN_PROGRESS",
    TripStatus.SUCCEEDED: "COMPLETED",
    TripStatus.FAILED: "FAILED",
    TripStatus.CANCELLED: "CANCELLED",
}


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
        if sherpa_summary["sherpa_status"]["mode"] == "error":
            agv_fault = {
                "messageType": "AgvFault",
                "externalReferenceId": externalReferenceId,
                "vehicleId": sherpa_summary["sherpa"]["hwid"],
                "vehicleTypeID": "ati-sherpa",
                "errorMessage": "ati-sherpa in error",
            }
            send_msg(agv_fault)
        else:
            agv_update = {
                "messageType": "AgvUpdate",
                "vehicleId": sherpa_summary["sherpa"]["hwid"],
                "vehicleTypeID": "ati-sherpa",
                "availability": sherpa_summary["sherpa_status"]["inducted"],
                "currentJobId": externalReferenceId,
                "currentActivity": AGV_ACTIVITY.driving,
                "nextActivity": AGV_ACTIVITY.unsupported,
                "mapPostion": {
                    "mapName": sherpa_summary["fleet_name"],
                    "positionX": sherpa_summary["sherpa_status"]["pose"][0],
                    "positionY": sherpa_summary["sherpa_status"]["pose"][1],
                    "positionZ": 0,
                    "orientation": sherpa_summary["sherpa_status"]["pose"][2],
                },
                "geoPosition": {
                    "logitude": 0,
                    "latitude": 0,
                    "elevation": 0,
                    "orientation": 0,
                },
                "speed": 1.0,
                "batteryLevel": None
                if sherpa_summary["sherpa_status"]["batteryLevel"] == -1
                else sherpa_summary["sherpa_status"]["batteryLevel"],
            }
            send_msg(agv_update)


# read status from periodic messages, for those trips in DB, send periodic msgs to IES.
def send_job_updates():
    logger = logging.getLogger("plugin_ies")
    while True:
        with session_maker() as db_session:
            all_active_trips = (
                db_session.query(TripsIES)
                .filter(TripsIES.status != TripStatus.CANCELLED)
                .filter(TripsIES.status != TripStatus.SUCCEEDED)
                .filter(TripsIES.status != TripStatus.FAILED)
                .all()
            )
            for trip in all_active_trips:
                # send_trip status req to FM using trip ID
                req_json = {"trip_ids": [trip.trip_id]}
                status_code, trip_status_response = send_req_to_FM(
                    "ies", "trip_status", req_type="post", req_json=req_json
                )
                if trip_status_response:
                    for trip_id, trip_details in trip_status_response.items():
                        send_agv_update_and_fault(
                            trip_details["sherpa_name"], trip.externalReferenceId
                        )
                        trip_status = trip_details["trip_details"]["status"]
                        next_idx_aug = trip_details["trip_details"]["next_idx_aug"]
                        if next_idx_aug == 0:
                            next_idx_aug = None
                        if trip_status == TripStatus.SUCCEEDED:
                            next_idx_aug = 0
                        msg_to_ies = {
                            "messageType": "JobUpdate",
                            "externalReferenceId": trip.externalReferenceId,
                            "lastCompletedTask": {
                                "ActionName": trip.actions[next_idx_aug - 1]
                                if next_idx_aug is not None
                                else "",
                                "LocationId": trip.locations[next_idx_aug - 1]
                                if next_idx_aug is not None
                                else "",
                            },
                            "jobStatus": IES_JOB_STATUS_MAPPING[trip_status],
                        }
                        logging.info(f"DB status: {trip.status}")
                        logging.info(f"FM Req status: {trip_status}")

                        if trip.status != trip_status:
                            logger.info(
                                f"trip_id: {trip_id}, FM_response_status: {trip_status}, db_status: {trip.status}"
                            )
                            send_msg(msg_to_ies)
                            trip.status = trip_status
                        elif trip.status == TripStatus.EN_ROUTE:
                            logger.info(
                                f"Trip status: {trip.status}, sending continuous updates!"
                            )
                            send_msg(msg_to_ies)

            db_session.commit()
            db_session.close()

        time.sleep(30)
