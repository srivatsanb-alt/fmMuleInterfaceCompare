import sys
import os
import json
import logging
import redis
from models.trip_models import TripStatus
from plugins.ies.ies_models import DBSession, IESBookingReq
from plugins.ies.ies_utils import (
    IES_JOB_STATUS_MAPPING,
    JobCreate,
    MsgToIES,
    get_ati_station_name,
    get_locationID_station_mapping,
)

sys.path.append("/app")
from plugins.plugin_comms import send_req_to_FM


class IES_HANDLER:
    def init_handler(self):
        self.redis_db = redis.from_url(os.getenv("FM_REDIS_URI"))
        self.locationID_station_mapping = get_locationID_station_mapping()
        self.plugin_name = "plugin_ies"

    def send_msg(self, msg):
        pub = redis.from_url(os.getenv("FM_REDIS_URI"), decode_responses=True)
        pub.publish("channel:plugin_ies", str(msg))

    def _get_ati_stations(self, tasklist):
        self.logger.info(f"tasklist: {tasklist}")
        route_stations = [
            None
            if task["LocationId"] not in self.locationID_station_mapping.keys()
            else get_ati_station_name(task["LocationId"])
            for task in tasklist
        ]
        return route_stations

    def handle(self, msg):
        self.logger = logging.getLogger("plugin_ies")
        self.logger.info(f"got a message {msg}")
        self.init_handler()
        msg_type = msg.get("messageType")
        valid_msg_types = ["JobCreate"]

        if msg_type not in valid_msg_types:
            self.logger.info(f"invalid message type, {msg}")
            return

        fn_handler = getattr(self, f"handle_{msg_type}", None)

        if not fn_handler:
            self.logger.info(f"Cannot handle msg, {msg}")
            return

        with DBSession() as db_session:
            self.session = db_session.session
            fn_handler(msg)
        return

    def handle_JobCreate(self, msg):
        self.logger.info("handling JobCreate...")
        job_create = JobCreate.from_dict(msg)
        rejected_msg = MsgToIES(
            "JobCreate", msg["externalReferenceId"], "REJECTED"
        ).to_dict()
        trip_ies = (
            self.session.query(IESBookingReq)
            .filter(IESBookingReq.ext_ref_id == job_create.externalReferenceId)
            .one_or_none()
        )
        self.logger.info(f"query resp: {trip_ies}")
        if trip_ies is not None:
            self.send_msg(rejected_msg)
            self.logger.info(
                f"Reference ID {job_create.externalReferenceId} already exists!"
            )
            return

        route_stations = self._get_ati_stations(job_create.taskList)
        self.logger.info(f"route stations: {route_stations}")
        if None in route_stations:
            ind = route_stations.index(None)
            self.send_msg(rejected_msg)
            self.logger.info(f"Can't find station {job_create.taskList[ind]}!")
            return

        accepted_msg = MsgToIES(
            "JobCreate", job_create.externalReferenceId, "ACCEPTED"
        ).to_dict()
        self.send_msg(accepted_msg)
        self.logger.info(f"adding trip to db")
        job = IESBookingReq(
            ext_ref_id=job_create.externalReferenceId,
            start_station=route_stations[0],
            route=route_stations,
            status=IES_JOB_STATUS_MAPPING[TripStatus.BOOKED],
            kanban_id=msg["properties"]["kanbanId"],
        )
        self.session.add(job)
        self.logger.info("added job, returning")
        return
