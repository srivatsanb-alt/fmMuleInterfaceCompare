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


def send_msg(msg):
    pub = redis.from_url(os.getenv("FM_REDIS_URI"), decode_responses=True)
    pub.publish("channel:plugin_ies", str(msg))


# read status from periodic messages, for those trips in DB, send periodic msgs to IES.
def send_job_updates():
    logger = logging.getLogger("plugin_ies")
    while True:
        with session_maker() as ies_db:
            all_active_trips = ies_db.query(TripsIES).all()
            for trip in all_active_trips:
                # send_trip status req to FM
                req_json = {"trip_ids": [trip.trip_id]}
                status_code, trip_status_response = send_req_to_FM(
                    "ies", "trip_status", req_type="post", req_json=req_json
                )
                logger.info(f"Response from FM: {status_code}, {trip_status_response}")
                if trip_status_response:
                    for trip_id, trip_details in trip_status_response.items():
                        trip_status = trip_details["trip_details"]["status"]
                        next_idx_aug = trip_details["trip_details"]["next_idx_aug"]
                        if trip.status != trip_status:
                            logger.info(f"trip_id: {trip_id}, last_known_status: {trip_status}, trip_status: {trip.status}")
                            trip.status = trip_status
                            # send_msg()
                        if next_idx_aug == 0:
                            next_idx_aug = None
                        if trip_status == TripStatus.SUCCEEDED:
                            next_idx_aug = 0

                msg_to_ies = {
                    "messageType": "JobUpdate",
                    "externalReferenceId": trip.externalReferenceId,
                    "lastCompletedTask": {
                        "ActionName": trip.actions[next_idx_aug - 1] if next_idx_aug is not None else "",
                        "LocationId": trip.locations[next_idx_aug - 1] if next_idx_aug is not None else "",
                    },
                    "jobStatus": IES_JOB_STATUS_MAPPING[trip_status]
                }
                send_msg(msg_to_ies)

            ies_db.commit()
            ies_db.close()

        time.sleep(30)
