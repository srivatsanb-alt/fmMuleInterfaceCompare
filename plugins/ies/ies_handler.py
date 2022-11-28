import sys
import os
import redis
import json
import logging

sys.path.append("/app")
from plugins.plugin_comms import send_req_to_FM
from .ies_utils import TripsIES, session
from utils.util import str_to_dt
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


class IES_HANDLER:
    def init_handler(self):
        locationID_station_mapper = os.path.join(
            os.getenv("FM_MAP_DIR"), "plugin_ies", "locationID_station_mapping.json"
        )
        with open(locationID_station_mapper, "r") as f:
            self.locationID_station_mapping = json.load(f)

        self.plugin_name = "plugin_ies"

    def close_db(self):
        session.commit()
        session.close()

    def send_msg(self, msg):
        pub = redis.from_url(os.getenv("FM_REDIS_URI"), decode_responses=True)
        pub.publish("channel:plugin_ies", str(msg))

    def handle_JobCreate(self, msg):

        msg_to_ies = {
            "messageType": "JobCreate",
            "externalReferenceId": msg["externalReferenceId"],
            "jobStatus": "REJECTED",
        }

        trip_ies: TripsIES = (
            session.query(TripsIES)
            .filter(TripsIES.externalReferenceId == msg["externalReferenceId"])
            .one_or_none()
        )
        if trip_ies:
            self.send_msg(msg_to_ies)
            return

        endpoint = "trip_book"
        routes = []
        priority = msg.get("priority", 1.0)
        for task in msg["taskList"]:
            try:
                station = self.locationID_station_mapping[task["locationId"]]
                routes.append(station)
            except:
                self.send_msg(msg_to_ies)
                return

        req_json = {"trips": [{"route": routes, "priority": priority}]}

        self.logger.info(f"sending trip book req to FM {req_json}")

        status_code, response_json = send_req_to_FM(
            self.plugin_name, endpoint, req_type="post", req_json=req_json
        )

        self.logger.info(f"Trip book response from FM {response_json}")

        if response_json is not None:
            msg_to_ies["jobStatus"] = "ACCEPTED"
            for trip_id, trip_details in response_json.items():
                trip = TripsIES(
                    trip_id=trip_id,
                    booking_id=trip_details["booking_id"],
                    externalReferenceId=msg["externalReferenceId"],
                    status=trip_details["status"],
                    actions=[tr.get("actionName", None) for tr in msg["taskList"]],
                    locations=[tr["locationId"] for tr in msg["taskList"]],
                )
                session.add(trip)
                self.logger.info(f"adding trip entry to db {trip.__dict__}")

        self.send_msg(msg_to_ies)

    def handle_JobCancel(self, msg):

        if not msg.get("externalReferenceId"):
            raise ValueError("JobCancel request sent without externalReferenceId")

        ext_ref_id = msg["externalReferenceId"]

        trip_ies: TripsIES = (
            session.query(TripsIES)
            .filter(TripsIES.externalReferenceId == ext_ref_id)
            .one_or_none()
        )

        if not trip_ies:
            msg_to_ies = {
                "messageType": "JobCancelResponse",
                "externalReferenceId": ext_ref_id,
                "jobStatus": "CANCELLED",
                "errorMessage ": f"unable to fetch trip details of trip: {ext_ref_id} from database",
            }
            self.send_msg(msg_to_ies)
            # raise ValueError(f"trip with externalReferenceId ext_ref_id not found")

        msg_to_ies = {
            "messageType": "JobCancelResponse",
            "externalReferenceId": ext_ref_id,
            "jobStatus": "CANCELLED",
            "errorMessage ": "Delete request rejected by fleet manager app",
        }

        try:
            status_req_json = {"trip_ids": [trip_ies.trip_id]}

            status_code, trip_status_response = send_req_to_FM(
                self.plugin_name, "trip_status", req_type="post", req_json=status_req_json
            )

            self.logger.info(
                f"trip_status_response {trip_status_response}, status_code: {status_code}"
            )

            trip_status = trip_status_response[str(trip_ies.trip_id)]["trip_details"][
                "status"
            ]
            booking_id = trip_status_response[str(trip_ies.trip_id)]["trip_details"][
                "booking_id"
            ]

            if trip_status in [TripStatus.EN_ROUTE, TripStatus.WAITING_STATION]:
                endpoint = "delete_ongoing_trip"
                return
            else:
                endpoint = "delete_booked_trip"

            status_code, delete_response = send_req_to_FM(
                self.plugin_name, endpoint, req_type="delete", query=booking_id
            )

            if status_code == 200:
                msg_to_ies = {
                    "messageType": "JobCancelResponse",
                    "externalReferenceId": ext_ref_id,
                    "jobStatus": "CANCELLED",
                }

                trip_ies.status = TripStatus.CANCELLED
                self.logger.info(
                    f"successfully deleted trip with externalReferenceId: {ext_ref_id}"
                )

        except:
            self.logger.info(
                f"unable to delete trip with externalReferenceId: {ext_ref_id}"
            )

        self.send_msg(msg_to_ies)

    def handle_JobQuery(self, msg):

        tz = os.getenv("PGTZ")
        trips_from = str_to_dt(msg["since"]).astimezone(tz)  # conv str to dt
        trips_till = str_to_dt(msg["until"]).astimezone(tz)  # UTC time to local time

        req_json = {"booked_from": trips_from, "booked_till": trips_till}

        status_code, trips_update_response = send_req_to_FM(
            self.plugin_name, "trip_status", req_type="post", req_json=req_json
        )

        # send update for all trips
        if trips_update_response:
            for trip_id, trip_details in trips_update_response.items():
                trip_ies = (
                    session.query(TripsIES)
                    .filter(TripsIES.trip_id == trip_id)
                    .one_or_none()
                )
                if trip_ies:
                    trip_status = trip_details["status"]
                    next_idx_aug = trip_details["next_idx_aug"]

                    if not next_idx_aug:
                        next_idx_aug = 0
                    if trip_status == TripStatus.SUCCEEDED:
                        next_idx_aug = -1

                    trip_ies.status = trip_status

                    msg_to_ies = {
                        "messageType": "JobUpdate",
                        "externalReferenceId": trip_ies.externalReferenceId,
                        "lastCompletedTask": {
                            "actionName": trip_ies.actions[next_idx_aug],
                            "locationId": trip_ies.locations[next_idx_aug],
                        },
                        "jobStatus": IES_JOB_STATUS_MAPPING[trip_status],
                    }

                    self.send_msg(msg_to_ies)

    def handle(self, msg):
        self.logger = logging.getLogger("plugin_ies")

        self.logger.info(f"got a message {msg}")
        self.init_handler()

        msg_type = msg.get("messageType")
        valid_msg_types = ["JobCreate", "JobCancel"]

        if msg_type not in valid_msg_types:
            self.logger.info(f"invalid message type, {msg}")
            return

        fn_handler = getattr(self, f"handle_{msg_type}", None)

        if not fn_handler:
            self.logger.info(f"Cannot handle msg, {msg}")
            return

        fn_handler(msg)

        self.close_db()
