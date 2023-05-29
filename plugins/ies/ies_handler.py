import sys
import os
import json
import logging
import redis
import pytz

from models.trip_models import TripStatus
import app.routers.dependencies as dpd
import plugins.ies.ies_models as im
import plugins.ies.ies_utils as iu

sys.path.append("/app")
from plugins.plugin_comms import send_req_to_FM


class IES_HANDLER:
    def init_handler(self):
        self.redis_db = redis.from_url(os.getenv("FM_REDIS_URI"))
        self.plugin_name = "plugin_ies"

    def send_msg(self, msg):
        pub = redis.from_url(os.getenv("FM_REDIS_URI"), decode_responses=True)
        pub.publish("channel:plugin_ies", str(msg))

    def _get_ati_stations(self, tasklist):
        all_ies_stations = [
            station.ies_name
            for station in self.dbsession.session.query(im.IESStations).all()
        ]
        self.logger.info(f"tasklist: {tasklist}")
        route_stations = [
            None
            if task["LocationId"] not in all_ies_stations
            else self.dbsession.get_ati_station_name(task["LocationId"])
            for task in tasklist
        ]
        return route_stations

    def _send_trip_book_req_fm(self, booking_route, sherpa_name):
        # giving higher priority to IES trips
        req_json = {
            "trips": [
                {
                    "route": booking_route,
                    "priority": 2,
                    "metadata": {"sherpa_name": sherpa_name},
                }
            ]
        }
        status_code, trip_booking_response = send_req_to_FM(
            "plugin_ies", "trip_book", req_type="post", req_json=req_json
        )
        return status_code, trip_booking_response

    def _get_booking(self, ref_id, raise_error=True):
        booking = (
            self.dbsession.session.query(im.IESBookingReq)
            .filter(im.IESBookingReq.ext_ref_id == ref_id)
            .one_or_none()
        )
        if booking is None and raise_error:
            raise ValueError(f"no booking entry with ref id {ref_id} in db")
        return booking

    def change_booking_req_status_and_update_IES(
        self, ext_ref_ids, status, combined_trip_id
    ):
        for ref_id in ext_ref_ids:
            self.logger.info(f"booking req: {ref_id}")
            booking_req = (
                self.dbsession.session.query(im.IESBookingReq)
                .filter(im.IESBookingReq.ext_ref_id == ref_id)
                .one_or_none()
            )
            if booking_req is None:
                raise ValueError(f"booking req {ref_id} not found in db")
            booking_req.status = status
            booking_req.combined_trip_id = combined_trip_id
            msg_to_ies = iu.MsgToIES(
                "JobUpdate", booking_req.ext_ref_id, iu.IES_JOB_STATUS_MAPPING[status]
            ).to_dict()
            self.logger.info(f"msg to ies: {msg_to_ies}")
            iu.send_msg_to_ies(msg_to_ies)
            # scheduled_msg_to_ies = iu.MsgToIES(
            #     "JobUpdate",
            #     booking_req.ext_ref_id,
            #     iu.IES_JOB_STATUS_MAPPING[TripStatus.ASSIGNED],
            # ).to_dict()
            # self.logger.info(f"scheduled msg to ies: {scheduled_msg_to_ies}")
            # iu.send_msg_to_ies(scheduled_msg_to_ies)

    def _add_combined_trip_to_db(self, response, booking_route, ext_ref_ids, sherpa_name):
        for trip_id, trip_details in response.items():
            status = trip_details["status"]
            combined_trip = im.CombinedTrips(
                trip_id=trip_id,
                booking_id=trip_details["booking_id"],
                combined_route=booking_route,
                status=status,
                sherpa=sherpa_name,
            )
            self.logger.info(f"adding combined trip to db")
            self.dbsession.add_to_session(combined_trip)
            self.logger.info(f"change booking req and update ies...")
            self.change_booking_req_status_and_update_IES(ext_ref_ids, status, trip_id)
            return

    def _send_scheduled_msgs(self, ext_ref_ids):
        for ref_id in ext_ref_ids:
            accepted_msg = iu.MsgToIES(
                "JobUpdate", ref_id, iu.IES_JOB_STATUS_MAPPING[TripStatus.BOOKED]
            ).to_dict()
            accepted_msg.update({"lastCompletedTask": ""})
            self.logger.info(f"sending accepted msg to IES, ref id {ref_id}")
            self.send_msg(accepted_msg)
            booking = self._get_booking(ref_id)
            self.logger.info(f"updating booking req status in db")
            booking.status = iu.IES_JOB_STATUS_MAPPING[TripStatus.BOOKED]

    def _get_route_tag(self, route_stations):
        all_ies_routes = self.dbsession.session.query(im.IESRoutes).all()
        res_tag = None
        for ies_route in all_ies_routes:
            intersection_route = list(
                set(route_stations).intersection(set(ies_route.route))
            )
            if len(intersection_route) == len(route_stations):
                res_tag = ies_route.route_tag
        return res_tag

    def _is_sherpa_at_start_station(self, sherpa_summary_response, route_tag):
        ies_route = iu.get_saved_route(route_tag)
        start_station = ies_route.route[0]
        sherpa_at_station = sherpa_summary_response["at_station"]
        return sherpa_at_station == start_station

    def _is_sherpa_ready_for_trip(self, sherpa_summary_response):
        sherpa_status = sherpa_summary_response["sherpa_status"]
        is_sherpa_idle = sherpa_status["idle"]
        is_sherpa_inducted = sherpa_status["inducted"]
        is_sherpa_disabled = sherpa_status["disabled"]
        sherpa_mode = sherpa_status["mode"]
        checks = [
            is_sherpa_idle is not False,
            is_sherpa_inducted is True,
            not is_sherpa_disabled,
            sherpa_mode == "fleet",
        ]
        error_msgs = [
            "not idle",
            "not inducted",
            "disconnected from FM",
            "not in fleet mode",
        ]
        false_idxs = [i for i, check in enumerate(checks) if check == False]
        return all(checks), [msg for i, msg in enumerate(error_msgs) if i in false_idxs]

    def handle_JobCreate(self, msg):
        self.logger.info("handling JobCreate...")
        job_create = iu.JobCreate.from_dict(msg)
        rejected_msg = iu.MsgToIES(
            "JobCreate", msg["externalReferenceId"], "REJECTED"
        ).to_dict()
        trip_ies = self._get_booking(job_create.externalReferenceId, raise_error=False)
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
            self.logger.info(
                f"Can't find station {job_create.taskList[ind]['LocationId']}!"
            )
            return
        route_tag = self._get_route_tag(route_stations)
        if route_tag is None:
            self.send_msg(rejected_msg)
            self.logger.info(f"Can't identify route_tag for route: {route_stations}")
            return
        self.logger.info(f"route stations: {route_stations}")

        accepted_msg = iu.MsgToIES(
            "JobCreate", job_create.externalReferenceId, "ACCEPTED"
        ).to_dict()
        self.send_msg(accepted_msg)
        self.logger.info(f"adding trip to db")
        tz = os.getenv("PGTZ")
        job = im.IESBookingReq(
            ext_ref_id=job_create.externalReferenceId,
            start_station=route_stations[0],
            route=route_stations,
            route_tag=route_tag,
            status="pending",
            kanban_id=msg["properties"]["kanbanId"],
            deadline=iu.dt_to_str(
                iu.str_to_dt_UTC(msg["deadline"] + " +0000").astimezone(pytz.timezone(tz))
            ),
            other_info={
                "material_no": msg["properties"]["materialNo"],
                "quantity": msg["properties"]["quantity"],
            },
        )
        self.dbsession.add_to_session(job)
        self.logger.info(f"added booking req {job_create.externalReferenceId}")
        ies_info = self.dbsession.session.query(im.IESInfo).first()
        are_route_stations_unique = len(set(route_stations)) == len(route_stations)
        if not ies_info.consolidate or not are_route_stations_unique:
            self.logger.info(f"consolidation is off, booking individual trip")
            req_msg = {
                "ext_ref_ids": [job_create.externalReferenceId],
                "route_tag": route_tag,
            }
            self.handle_book_consolidated_trip(req_msg)
        return

    def handle_JobQuery(self, msg):
        self.logger.info("handling JobQuery...")
        job_query = iu.JobQuery.from_dict(msg)
        tz = os.getenv("PGTZ")
        jobs_from = iu.str_to_dt_UTC(
            job_query.since[:-2] + " +0000", query=True
        ).astimezone(pytz.timezone(tz))
        jobs_till = iu.str_to_dt_UTC(
            job_query.until[:-2] + " +0000", query=True
        ).astimezone(pytz.timezone(tz))
        self.logger.info(f"from: {jobs_from}; till: {jobs_till}")
        jobs = self.dbsession.get_jobs_between_time(jobs_from, jobs_till)
        self.logger.info(f"jobs: {jobs}")
        for job in jobs:
            iu.compose_and_send_job_update_msg(
                job.ext_ref_id,
                job.status,
                job.combined_trip.combined_route if job.combined_trip else "None",
                job.combined_trip.next_idx_aug if job.combined_trip else 0,
            )
        return

    def handle_JobCancel(self, msg):
        self.logger.info("handling JobCancel...")
        job_cancel = iu.JobCancel.from_dict(msg)
        ext_ref_id = job_cancel.externalReferenceId
        rejected_msg = iu.MsgToIES("JobCancel", ext_ref_id, "REJECTED").to_dict()
        booking_req = (
            self.dbsession.session.query(im.IESBookingReq)
            .filter(im.IESBookingReq.ext_ref_id == ext_ref_id)
            .one_or_none()
        )
        if booking_req == None:
            self.send_msg(rejected_msg)
            self.logger.info(
                f"can't find job with ref id: {ext_ref_id}, rejecting JobCancel"
            )
            return
        job_status = booking_req.status
        if job_status != "pending":
            self.send_msg(rejected_msg)
            self.logger.info(
                f"can't cancel consolidated booking with ref id: {ext_ref_id}, rejecting JobCancel"
            )
            return
        cancelled_msg = iu.MsgToIES("JobCancel", ext_ref_id, "CANCELLED").to_dict()
        booking_req.status = TripStatus.CANCELLED
        self.logger.info(f"cancelling job with ref id: {ext_ref_id}")
        self.send_msg(cancelled_msg)
        return

    def handle_add_ies_station(self, msg):
        add_station = iu.StationIES.from_dict(msg)
        self.logger.info("handling add_ies_station")

        ati_name_station = iu.get_ies_station(
            self.dbsession, ati_station_name=add_station.ati_name
        )
        ies_name_station = iu.get_ies_station(
            self.dbsession, ies_station_name=add_station.ies_name
        )
        # if station already exists..
        if ati_name_station is not None and ies_name_station is None:
            ati_name_station.ies_name = add_station.ies_name
            return

        elif ies_name_station is not None:
            logging.info(f"ies name is not unique")
            raise ValueError(f"IES name ({add_station.ies_name}) already exists")

        ies_station = im.IESStations(
            ies_name=add_station.ies_name,
            ati_name=add_station.ati_name,
        )
        self.logger.info(f"adding station ({msg}) to db")
        self.dbsession.add_to_session(ies_station)
        return

    def handle_book_consolidated_trip(self, msg):
        ext_ref_ids = msg["ext_ref_ids"]
        ies_info = self.dbsession.session.query(im.IESInfo).first()
        max_bookings = ies_info.max_bookings
        if not len(ext_ref_ids) < max_bookings:
            raise ValueError(
                f"Please select less than {max_bookings} requests to consolidate."
            )
        route_tag = msg["route_tag"]
        sherpa_name = msg["sherpa"]
        unsorted_route_stations = []
        for ref_id in ext_ref_ids:
            ies_booking = self._get_booking(ref_id)
            unsorted_route_stations.extend(station for station in ies_booking.route)
        self.logger.info(f"unsorted_route_stations: {unsorted_route_stations}")
        unique_stations = list(set(unsorted_route_stations))
        all_ies_routes = self.dbsession.get_all_ies_routes()
        if route_tag not in all_ies_routes.keys():
            raise ValueError(
                f"IES route ({route_tag} not found in db, can't consolidate trip)"
            )
        route = all_ies_routes[route_tag]
        booking_route = [station for station in route if station in unique_stations]
        sherpa_summary_response = iu.get_sherpa_summary_for_sherpa(sherpa_name)
        if not self._is_sherpa_at_start_station(sherpa_summary_response, route_tag):
            raise ValueError(
                f"sherpa {sherpa_name} moved away from start station on route {route_tag}, can't consolidate trip"
            )
        is_sherpa_ready, reasons = self._is_sherpa_ready_for_trip(sherpa_summary_response)
        if not is_sherpa_ready:
            raise ValueError(
                f"sherpa is {', '.join(reason for reason in reasons)}, can't consolidate trip"
            )
        status_code, response = self._send_trip_book_req_fm(booking_route, sherpa_name)
        if status_code != 200:
            raise ValueError(f"{status_code}: consolidated trip booking req failed")
        self.logger.info(f"trip booked: {response.keys()}")
        self._add_combined_trip_to_db(response, booking_route, ext_ref_ids, sherpa_name)
        return

    def handle(self, msg):
        self.logger = logging.getLogger("plugin_ies")
        self.logger.info(f"got a message {msg}")
        self.init_handler()
        msg_type = msg.get("messageType")
        invalid_msg_types = []

        if msg_type in invalid_msg_types:
            self.logger.info(f"invalid message type, {msg}")
            return

        fn_handler = getattr(self, f"handle_{msg_type}", None)

        if not fn_handler:
            self.logger.info(f"Cannot handle msg, {msg}")
            return

        with im.DBSession() as db_session:
            self.dbsession = db_session
            fn_handler(msg)
        return
