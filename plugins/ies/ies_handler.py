import sys
import os
import redis
import json
import logging
import pytz

sys.path.append("/app")
from plugins.plugin_comms import send_req_to_FM

from .ies_utils import (
    TripsIES,
    session,
    JobCreate,
    JobCancel,
    JobQuery,
    MsgToIES,
    IES_JOB_STATUS_MAPPING,
    read_dict_var_from_redis_db,
    get_locationID_station_mapping,
    get_ati_station_name,
    remove_from_pending_jobs_db,
)
from utils.util import str_to_dt, str_to_dt_UTC, dt_to_str
from models.trip_models import TripStatus
from models.base_models import JsonMixin


class IES_HANDLER:
    def init_handler(self):
        self.redis_db = redis.from_url(os.getenv("FM_REDIS_URI"))
        self.locationID_station_mapping = get_locationID_station_mapping()
        self.plugin_name = "plugin_ies"

    def close_db(self):
        session.commit()
        session.close()

    def send_msg(self, msg):
        pub = redis.from_url(os.getenv("FM_REDIS_URI"), decode_responses=True)
        pub.publish("channel:plugin_ies", str(msg))

    def handle(self, msg):
        self.logger = logging.getLogger("plugin_ies")
        self.logger.info(f"got a message {msg}")
        self.init_handler()
        msg_type = msg.get("messageType")
        valid_msg_types = ["JobCreate", "JobCancel", "JobQuery"]

        if msg_type not in valid_msg_types:
            self.logger.info(f"invalid message type, {msg}")
            return

        fn_handler = getattr(self, f"handle_{msg_type}", None)

        if not fn_handler:
            self.logger.info(f"Cannot handle msg, {msg}")
            return

        fn_handler(msg)
        self.close_db()
        return

    def handle_JobCreate(self, msg: dict):
        job_create = JobCreate.from_dict(msg)
        rejected_msg = MsgToIES(
            "JobCreate", msg["externalReferenceId"], "REJECTED"
        ).to_dict()

        trip_ies = query_ref_id(job_create.externalReferenceId)
        if trip_ies is not None:
            self.send_msg(rejected_msg)
            self.logger.info(
                f"Reference ID {job_create.externalReferenceId} already exists!"
            )
            return
        route_stations = self._get_ati_stations(job_create.taskList)
        if None in route_stations:
            ind = route_stations.index(None)
            self.send_msg(rejected_msg)
            self.logger.info(f"Can't find station {job_create.taskList[ind]}!")
            return
        status_code, response_json = self._get_job_create_response(
            job_create, route_stations
        )
        if response_json is None:
            self.logger.info(
                f"req to FM failed, response json: {response_json} response code: {status_code}"
            )
            self.send_msg(rejected_msg)
        else:
            accepted_msg = MsgToIES(
                "JobCreate", msg["externalReferenceId"], "ACCEPTED"
            ).to_dict()
            self.send_msg(accepted_msg)
            self._process_job_create_response(response_json, job_create)
        return

    def _add_to_pending_jobs_db(self, job_create):
        jobs_list = read_dict_var_from_redis_db(self.redis_db, "pending_jobs")
        new_job = {
            job_create.externalReferenceId: {
                "taskList": job_create.taskList,
                "priority": job_create.priority,
            }
        }
        jobs_list.update(new_job)
        self.redis_db.set("pending_jobs", json.dumps(jobs_list))
        return

    def handle_JobCancel(self, msg):
        job_cancel = JobCancel.from_dict(msg)
        if "externalReferenceId" not in msg.keys():
            raise ValueError("JobCancel request sent without externalReferenceId")
        ext_ref_id = job_cancel.externalReferenceId
        trip_ies = query_ref_id(ext_ref_id)
        if trip_ies is None:
            cancelled_msg_to_ies = MsgToIES(
                "JobCancelResponse", ext_ref_id, "CANCELLED"
            ).to_dict()
            cancelled_msg_to_ies.update(
                {
                    "errorMessage": f"unable to fetch trip details of trip: {ext_ref_id} from database"
                }
            )
            self.send_msg(cancelled_msg_to_ies)
            return
        self._process_job_cancel_msg(trip_ies, ext_ref_id)
        return

    def _process_job_cancel_msg(self, trip_ies, ext_ref_id):
        try:
            msg_to_ies = MsgToIES("JobCancelResponse", ext_ref_id, "CANCELLED").to_dict()
            status_code, trip_status_response = send_req_to_FM(
                self.plugin_name,
                "trip_status",
                req_type="post",
                req_json={"trip_ids": [trip_ies.trip_id]},
            )
            self.logger.debug(
                f"trip_status_response {trip_status_response}, status_code: {status_code}"
            )
            trip_details = trip_status_response[str(trip_ies.trip_id)]["trip_details"]

            if trip_details["status"] in [TripStatus.EN_ROUTE, TripStatus.WAITING_STATION]:
                endpoint = "delete_ongoing_trip"
            else:
                endpoint = "delete_booked_trip"
            status_code, _ = send_req_to_FM(
                self.plugin_name,
                endpoint,
                req_type="delete",
                query=trip_details["booking_id"],
            )
            if status_code == 200:
                self.logger.info(
                    f"successfully deleted trip externalReferenceId: {ext_ref_id}"
                )
                self.send_msg(msg_to_ies)
                remove_from_pending_jobs_db(self.redis_db, ext_ref_id)
        except:
            self.logger.info(f"unable to delete trip externalReferenceId: {ext_ref_id}")
            msg_to_ies.update(
                {"errorMessage": "Delete request rejected by fleet manager app"}
            )
            self.send_msg(msg_to_ies)
        return

    def handle_JobQuery(self, msg):
        trips_update_response = self._process_job_query_msg(msg)
        # send update for all trips
        if trips_update_response is not None:
            for trip_id, trip_details in trips_update_response.items():
                trip_ies = query_trip_id(trip_id)
                if trip_ies is not None:
                    msg_to_ies = self._get_job_query_msg(trip_details, trip_ies)
                    self.send_msg(msg_to_ies)
        else:
            msg_to_ies = MsgToIES("JobUpdate", "None", "None").to_dict()
            msg_to_ies.update({"lastCompletedTask": "No Trips"})
            self.send_msg(msg_to_ies)
        return

    def _get_ati_stations(self, tasklist):
        route_stations = [
            None
            if task["LocationId"] not in self.locationID_station_mapping.keys()
            else get_ati_station_name([task["LocationId"]])
            for task in tasklist
        ]
        return route_stations

    def _get_job_create_response(self, job_create, route_stations):
        req_json = {"trips": [{"route": route_stations, "priority": job_create.priority}]}
        self.logger.info(f"sending trip book req to FM {req_json}")
        status_code, response_json = send_req_to_FM(
            self.plugin_name, "trip_book", req_type="post", req_json=req_json
        )
        self.logger.debug(f"Trip book response from FM {response_json}")
        return status_code, response_json

    def _process_job_query_msg(self, msg):
        job_query = JobQuery.from_dict(msg)
        tz = os.getenv("PGTZ")
        # enforcing UTC time zone info here (+0000), need to check Bosch's msg format!
        trips_from = str_to_dt_UTC(job_query.since + " +0000").astimezone(
            pytz.timezone(tz)
        )  # conv str to dt
        trips_till = str_to_dt_UTC(job_query.until + " +0000").astimezone(
            pytz.timezone(tz)
        )  # UTC time to local time

        req_json = {
            "booked_from": dt_to_str(trips_from),
            "booked_till": dt_to_str(trips_till),
        }
        # trips_from, trips_till, req_json =
        _, trips_update_response = send_req_to_FM(
            self.plugin_name, "trip_status", req_type="post", req_json=req_json
        )
        return trips_update_response

    def _get_job_query_msg(self, ies_msg, trip_ies):
        trip_status = ies_msg["trip_details"]["status"]
        next_idx_aug = ies_msg["trip_details"]["next_idx_aug"]
        self.logger.debug(f"Trip status, next_idx = {trip_status, next_idx_aug}")

        if next_idx_aug == 0:
            next_idx_aug = None
        if trip_status == TripStatus.SUCCEEDED:
            next_idx_aug = 0

        trip_ies.status = trip_status
        msg_to_ies = MsgToIES(
            "JobUpdate", trip_ies.externalReferenceId, IES_JOB_STATUS_MAPPING[trip_status]
        ).to_dict()
        msg_to_ies.update(
            {
                "lastCompletedTask": {
                    "ActionName": trip_ies.actions[next_idx_aug - 1]
                    if next_idx_aug is not None
                    else "",
                    "LocationId": trip_ies.locations[next_idx_aug - 1]
                    if next_idx_aug is not None
                    else "",
                }
            }
        )
        return msg_to_ies

    def _process_job_create_response(self, response_json, job_create):
        for trip_id, trip_details in response_json.items():
            trip = TripsIES(
                trip_id=trip_id,
                booking_id=trip_details["booking_id"],
                externalReferenceId=job_create.externalReferenceId,
                status=trip_details["status"],
                actions=[task.get("ActionName", None) for task in job_create.taskList],
                locations=[task["LocationId"] for task in job_create.taskList],
            )
            session.add(trip)
            self.logger.debug(f"adding trip entry to db {trip.__dict__}")
            if trip_details["status"] == TripStatus.BOOKED:
                msg_to_ies = MsgToIES(
                    "JobUpdate",
                    job_create.externalReferenceId,
                    IES_JOB_STATUS_MAPPING[trip_details["status"]],
                ).to_dict()
                msg_to_ies.update(
                    {"lastCompletedTask": {"ActionName": "", "LocationId": ""}}
                )
                self.logger.info(
                    "Sending JobUpdate {booked_msg_to_ies} to IES in JobCreate"
                )
                self.send_msg(msg_to_ies)
                self._add_to_pending_jobs_db(job_create)
        return


def query_trip_id(trip_id):
    return session.query(TripsIES).filter(TripsIES.trip_id == trip_id).one_or_none()


def query_ref_id(ref_id):
    return (
        session.query(TripsIES).filter(TripsIES.externalReferenceId == ref_id).one_or_none()
    )

