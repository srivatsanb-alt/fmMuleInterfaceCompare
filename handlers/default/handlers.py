import os
import datetime
import logging
import logging.config
from typing import List
import redis
from requests import Response
from sqlalchemy.orm.attributes import flag_modified

# ati code imports
import models.fleet_models as fm
import models.misc_models as mm
import models.request_models as rqm
import models.trip_models as tm
import models.visa_models as vm
from models.base_models import StationProperties
from models.db_session import DBSession
from models.mongo_client import FMMongo
import utils.log_utils as lu
import utils.comms as utils_comms
import utils.util as utils_util
import utils.visa_utils as utils_visa
import core.constants as cc

from optimal_dispatch.dispatcher import OptimalDispatch
import handlers.default.handler_utils as hutils


# get log config
logging.config.dictConfig(lu.get_log_config_dict())


class RequestContext:
    msg_type: str
    sherpa_name: str
    fleet_names: List[str]


req_ctxt = RequestContext()


def init_request_context(req):
    req_ctxt.msg_type = req.type
    req_ctxt.source = req.source
    req_ctxt.fleet_names = []
    if isinstance(req, rqm.SherpaReq) or isinstance(req, rqm.SherpaMsg):
        req_ctxt.sherpa_name = req.source
        req_ctxt.source = req.source
    else:
        req_ctxt.sherpa_name = None


class Handlers:
    def should_handle_msg(self, msg):
        sherpa_name = req_ctxt.sherpa_name
        if not sherpa_name:
            return True, None

        sherpa: fm.Sherpa = self.dbsession.get_sherpa(sherpa_name)
        fleet: fm.Fleet = sherpa.fleet

        if fleet.name not in req_ctxt.fleet_names:
            req_ctxt.fleet_names.append(sherpa.fleet.name)

        if fleet.status == cc.FleetStatus.PAUSED and msg.type not in [
            cc.MessageType.SHERPA_STATUS,
        ]:
            return False, f"fleet {fleet.name} is paused"

        return True, None

    def record_msg_received(self, msg, update_msgs):

        # add the message received to sherpa events
        if req_ctxt.sherpa_name and msg.type not in update_msgs:
            hutils.add_sherpa_event(
                self.dbsession, req_ctxt.sherpa_name, msg.type, "sent by sherpa"
            )

        if msg.type in update_msgs:
            logging.getLogger("status_updates").info(f"{req_ctxt.sherpa_name} :  {msg}")

        elif msg.type == cc.MessageType.RESOURCE_ACCESS:
            logging.getLogger("visa").info(
                f"Got message of type {msg.type} from {req_ctxt.source} \n Message: {msg} \n"
            )

        else:
            logging.getLogger().info(
                f"Got message of type {msg.type} from {req_ctxt.source} \n Message: {msg} \n"
            )

    def ignore_msg(self, msg, update_msgs, reason):
        if msg.type in update_msgs:
            logging.getLogger("status_updates").warning(
                f"message of type {msg.type} ignored, reason={reason}"
            )
        else:
            logging.getLogger().warning(
                f"message of type {msg.type} ignored, reason={reason}"
            )

    def run_health_check(self):
        # have not seperated queries and DB - Need to be done
        hutils.check_sherpa_status(self.dbsession)
        hutils.delete_notifications(self.dbsession)
        redis_conn = redis.from_url(os.getenv("FM_REDIS_URI"))
        current_data_folder = redis_conn.get("current_data_folder").decode()
        hutils.record_cpu_perf(current_data_folder)
        hutils.record_rq_perf(current_data_folder)
        logging.getLogger("status_updates").info("Ran a FM health check")

    def run_misc_processes(self):
        # have not seperated queries and DB - Need to be done
        hutils.update_sherpa_oee(self.dbsession)

    def get_sherpa_trips(self, sherpa_name):
        sherpa: fm.Sherpa = self.dbsession.get_sherpa(sherpa_name)

        if sherpa is None:
            raise ValueError(f"{sherpa_name} not found in DB")

        ongoing_trip: tm.OngoingTrip = self.dbsession.get_ongoing_trip(sherpa.name)
        pending_trip: tm.PendingTrip = self.dbsession.get_pending_trip(sherpa.name)
        return sherpa, ongoing_trip, pending_trip

    def initialize_sherpa(self, sherpa: fm.Sherpa):
        sherpa_status: fm.SherpaStatus = sherpa.status
        sherpa_status.initialized = True
        sherpa_status.continue_curr_task = True
        logging.getLogger("status_updates").info(f"{sherpa.name} initialized")

    def update_sherpa_info(self, sherpa_status: fm.SherpaStatus, init_response: dict):

        if sherpa_status.other_info is None:
            sherpa_status.other_info = {}
        sherpa_status.other_info.update(
            {"last_software_update": init_response.get("last_updated")}
        )
        sherpa_status.other_info.update({"sw_date": init_response.get("sw_date")})
        sherpa_status.other_info.update({"sw_tag": init_response.get("sw_tag")})
        sherpa_status.other_info.update({"sw_id": init_response.get("sw_id")})

        flag_modified(sherpa_status, "other_info")
        logging.getLogger("status_updates").info(
            f"updated {sherpa_status.sherpa_name} build info {sherpa_status.other_info}"
        )

    def check_if_booking_is_valid(
        self, trip_msg: rqm.TripMsg, all_stations: List[fm.Station]
    ):
        reason = None
        if trip_msg.priority <= 0.0:
            reason = f"trip priority cannot be less than/ equal to zero, priority: {trip_msg.priority}"

        for station in all_stations:
            if any(
                prop in station.properties
                for prop in [StationProperties.CONVEYOR, StationProperties.CHUTE]
            ):
                trip_metadata = trip_msg.metadata

                # convert string to bool
                trip_metadata["conveyor_ops"] = True

                num_units = hutils.get_conveyor_ops_info(trip_metadata)

                if num_units is None:
                    raise ValueError("No tote/units information present")

                if num_units > 2 or num_units < 0:
                    reason = f"num units for conveyor transaction cannot be greater than 2 or less than 0, num_units_input: {num_units}"
                    raise ValueError(f"{reason}")

            if station.status.disabled is True:
                raise ValueError(
                    f"Cannot accept the trip booking since {station.name} is disabled"
                )

    def should_recreate_scheduled_trip(self, pending_trip: tm.PendingTrip):
        trip_metadata = pending_trip.trip.trip_metadata
        scheduled_end_time = utils_util.str_to_dt(trip_metadata["scheduled_end_time"])

        if not utils_util.check_if_timestamp_has_passed(scheduled_end_time):
            new_metadata = pending_trip.trip.trip_metadata
            time_period = new_metadata["scheduled_time_period"]
            new_start_time = datetime.datetime.now() + datetime.timedelta(
                seconds=int(time_period)
            )
            if new_start_time > scheduled_end_time:
                logging.getLogger().info(
                    f"will not recreate trip {pending_trip.trip.id}, new trip start_time past scheduled_end_time"
                )
                return

            logging.getLogger().info(
                f"recreating trip {pending_trip.trip.id}, scheduled trip needs to be continued"
            )

            new_start_time = utils_util.dt_to_str(new_start_time)
            new_metadata["scheduled_start_time"] = new_start_time
            logging.getLogger().info(f"scheduled new metadata {new_metadata}")
            new_trip: tm.Trip = self.dbsession.create_trip(
                pending_trip.trip.route,
                pending_trip.trip.priority,
                new_metadata,
                pending_trip.trip.booking_id,
                pending_trip.trip.fleet_name,
                pending_trip.trip.booked_by,
            )
            self.dbsession.create_pending_trip(new_trip.id)
        else:
            logging.getLogger().info(
                f"will not recreate trip {pending_trip.trip.id}, scheduled_end_time past current time"
            )

    def assign_new_trip(
        self,
        sherpa: fm.Sherpa,
        pending_trip: tm.PendingTrip,
        all_stations: List[fm.Station],
    ):
        fleet: fm.Fleet = sherpa.fleet

        if fleet.status == cc.FleetStatus.STOPPED:
            logging.getLogger(sherpa.name).info(
                f"fleet {fleet.name} is stopped, not assigning new trip to {sherpa.name}"
            )
            return False

        if not pending_trip:
            return False

        logging.getLogger(sherpa.name).info(
            f"found pending trip id {pending_trip.trip_id}, route: {pending_trip.trip.route}"
        )

        sherpa_status: fm.SherpaStatus = sherpa.status
        sherpa_status.continue_curr_task = False

        if not hutils.is_sherpa_available_for_new_trip(sherpa_status):
            logging.getLogger(sherpa.name).info(
                f"{sherpa.name} not available for {pending_trip.trip_id}"
            )
            return False

        if pending_trip.trip.scheduled:
            self.should_recreate_scheduled_trip(pending_trip)

        self.start_trip(pending_trip.trip, sherpa, all_stations)
        self.dbsession.delete_pending_trip(pending_trip)
        logging.getLogger(sherpa.name).info(
            f"deleted pending trip id {pending_trip.trip_id}"
        )
        return True

    def start_trip(self, trip: tm.Trip, sherpa: fm.Sherpa, all_stations: List[fm.Station]):
        ongoing_trip = hutils.assign_sherpa(self.dbsession, trip, sherpa)
        hutils.start_trip(self.dbsession, ongoing_trip, sherpa, all_stations)

    def end_trip(
        self,
        ongoing_trip: tm.OngoingTrip,
        sherpa: fm.Sherpa,
        success: bool = True,
    ):
        if not ongoing_trip:
            return
        sherpa_name = ongoing_trip.sherpa_name
        hutils.end_trip(self.dbsession, ongoing_trip, sherpa, success)
        logging.getLogger(sherpa_name).info(f"trip {ongoing_trip.trip_id} finished")

    def start_leg(
        self,
        ongoing_trip: tm.OngoingTrip,
        sherpa: fm.Sherpa,
        from_station: fm.Station,
        to_station: fm.Station,
    ):
        trip: tm.Trip = ongoing_trip.trip
        fleet: fm.Fleet = sherpa.fleet

        if not ongoing_trip.sherpa_name:
            raise ValueError(f"cannot start leg of unassigned trip {trip.id}")

        if ongoing_trip.finished():
            raise ValueError(f"{sherpa.name} cannot start leg of finished trip {trip.id}")

        ongoing_trip.clear_states()
        self.do_pre_actions(ongoing_trip)

        hutils.start_leg(self.dbsession, ongoing_trip, from_station, to_station)
        sherpa.status.trip_leg_id = ongoing_trip.trip_leg_id

        from_station_name = from_station.name if from_station else None
        started_leg_log = f"{sherpa.name} started a trip leg of trip (trip_id: {trip.id}) from {from_station_name} to {to_station.name}"

        logging.getLogger(sherpa.name).info(started_leg_log)

        _: Response = utils_comms.send_move_msg(
            self.dbsession, sherpa, ongoing_trip, to_station
        )

        self.dbsession.add_notification(
            [sherpa.name, fleet.name, fleet.customer],
            started_leg_log,
            mm.NotificationLevels.info,
            mm.NotificationModules.trip,
        )

    def end_leg(
        self,
        ongoing_trip: tm.OngoingTrip,
        sherpa: fm.Sherpa,
        curr_station: fm.Station,
        trip_analytics: tm.TripAnalytics,
    ):
        trip: tm.Trip = ongoing_trip.trip
        sherpa_name = trip.sherpa_name

        end_leg_log = f"{sherpa_name} finished a trip leg of trip (trip_id: {trip.id}) from {ongoing_trip.trip_leg.from_station} to {ongoing_trip.trip_leg.to_station}"
        logging.getLogger(sherpa_name).info(end_leg_log)

        hutils.end_leg(ongoing_trip)
        sherpa.status.trip_leg_id = None

        if trip_analytics:
            trip_analytics.end_time = datetime.datetime.now()
            time_delta = datetime.datetime.now() - ongoing_trip.trip_leg.start_time
            trip_analytics.actual_trip_time = time_delta.seconds
            trip_analytics.progress = 1.0

        self.do_post_actions(ongoing_trip, sherpa, curr_station)
        self.dbsession.add_notification(
            [sherpa.name, sherpa.fleet.name, sherpa.fleet.customer],
            end_leg_log,
            mm.NotificationLevels.info,
            mm.NotificationModules.trip,
        )

    def continue_leg(
        self,
        ongoing_trip: tm.OngoingTrip,
        sherpa: fm.Sherpa,
        from_station: fm.Station,
        to_station: fm.Station,
    ):
        trip: tm.Trip = ongoing_trip.trip
        sherpa.status.continue_curr_task = False

        logging.getLogger(sherpa.name).info(
            f"{sherpa.name} continuing leg of trip {trip.id} from {ongoing_trip.curr_station()} to {ongoing_trip.next_station()}"
        )
        _: Response = utils_comms.send_move_msg(
            self.dbsession, sherpa, ongoing_trip, to_station
        )

    def check_start_new_leg(self, ongoing_trip: tm.OngoingTrip):
        if not ongoing_trip:
            return False
        if not ongoing_trip.trip_leg:
            return True
        if ongoing_trip.trip_leg.finished():
            return True

    def check_continue_curr_leg(self, ongoing_trip: tm.OngoingTrip):
        return (
            ongoing_trip and ongoing_trip.trip_leg and not ongoing_trip.trip_leg.finished()
        )

    # run optimal_dispatch
    def run_optimal_dispatch(self, fleet_names):
        with FMMongo() as fm_mongo:
            optimal_dispatch_config = fm_mongo.get_document_from_fm_config(
                "optimal_dispatch"
            )

        optimal_dispatch = OptimalDispatch(optimal_dispatch_config)
        optimal_dispatch.run(self.dbsession, fleet_names)

    def do_pre_actions(self, ongoing_trip: tm.OngoingTrip):
        curr_station = ongoing_trip.curr_station()
        sherpa_name = ongoing_trip.sherpa_name
        if not curr_station:
            logging.getLogger(sherpa_name).info(
                f"no pre-actions performed since {sherpa_name} is not at a trip station"
            )
            return

    def record_dispatch_wait_start(self, ongoing_trip: tm.OngoingTrip):
        trip_metadata = ongoing_trip.trip.trip_metadata
        if trip_metadata is None:
            trip_metadata = {}
        trip_metadata.update(
            {"dispatch_wait_start": utils_util.dt_to_str(datetime.datetime.now())}
        )
        flag_modified(ongoing_trip.trip, "trip_metadata")

    def record_dispatch_wait_end(self, ongoing_trip: tm.OngoingTrip):
        trip_metadata = ongoing_trip.trip.trip_metadata
        if trip_metadata is None:
            return

        dispatch_start = trip_metadata.get("dispatch_wait_start", None)
        if dispatch_start:
            dispatch_start_dt = utils_util.str_to_dt(dispatch_start)
            disaptch_wait = datetime.datetime.now() - dispatch_start_dt

            total_dispatch_wait_time = trip_metadata.get("total_dispatch_wait_time", None)

            if total_dispatch_wait_time is None:
                total_dispatch_wait_time = 0

            trip_metadata.update({"total_dispatch_wait_time": str(disaptch_wait.seconds)})
            del trip_metadata["dispatch_wait_start"]
            flag_modified(ongoing_trip.trip, "trip_metadata")

    def add_dispatch_start_to_ongoing_trip(
        self, ongoing_trip: tm.OngoingTrip, sherpa: fm.Sherpa, timeout=False
    ):
        ongoing_trip.add_state(tm.TripState.WAITING_STATION_DISPATCH_START)
        dispatch_mesg = rqm.DispatchButtonReq(value=True)
        if timeout:

            with FMMongo() as fm_mongo:
                station_config = fm_mongo.get_document_from_fm_config("stations")

            dispatch_timeout = station_config["dispatch_timeout"]
            dispatch_mesg = rqm.DispatchButtonReq(value=True, timeout=dispatch_timeout)

        sherpa_action_msg = rqm.PeripheralsReq(
            dispatch_button=dispatch_mesg,
            speaker=rqm.SpeakerReq(sound=rqm.SoundEnum.wait_for_dispatch, play=True),
            indicator=rqm.IndicatorReq(
                pattern=rqm.PatternEnum.wait_for_dispatch, activate=True
            ),
        )
        _ = utils_comms.send_req_to_sherpa(self.dbsession, sherpa, sherpa_action_msg)
        self.record_dispatch_wait_start(ongoing_trip)

    def add_auto_hitch_start_to_ongoing_trip(
        self, ongoing_trip: tm.OngoingTrip, sherpa: fm.Sherpa
    ):
        ongoing_trip.add_state(tm.TripState.WAITING_STATION_AUTO_HITCH_START)
        hitch_msg = rqm.PeripheralsReq(auto_hitch=rqm.HitchReq(hitch=True))
        _ = utils_comms.send_req_to_sherpa(self.dbsession, sherpa, hitch_msg)

    def add_auto_unhitch_start_to_ongoing_trip(
        self, ongoing_trip: tm.OngoingTrip, sherpa: fm.Sherpa
    ):
        ongoing_trip.add_state(tm.TripState.WAITING_STATION_AUTO_UNHITCH_START)
        unhitch_msg = rqm.PeripheralsReq(auto_hitch=rqm.HitchReq(hitch=False))
        _ = utils_comms.send_req_to_sherpa(self.dbsession, sherpa, unhitch_msg)

    def add_conveyor_start_to_ongoing_trip(
        self, ongoing_trip: tm.OngoingTrip, sherpa: fm.Sherpa, station: fm.Station
    ):
        direction = "send" if StationProperties.CHUTE in station.properties else "receive"
        station_type = (
            "chute" if StationProperties.CHUTE in station.properties else "conveyor"
        )

        conveyor_start_state = getattr(
            tm.TripState, f"WAITING_STATION_CONV_{direction.upper()}_START"
        )

        trip_metadata = ongoing_trip.trip.trip_metadata
        if direction == "receive":
            num_units = utils_comms.get_num_units_converyor(station.name)
            # update metadata with num totes for dropping totes at chute
            trip_metadata["num_units"] = num_units
            flag_modified(ongoing_trip.trip, "trip_metadata")

        else:
            num_units = trip_metadata.get("num_units", None)
            if num_units is None:
                raise ValueError("No tote/units information present")

        if num_units == 0:
            logging.getLogger(sherpa.name).info(
                f"will not send conveyor msg to {ongoing_trip.sherpa_name}, reason: num_units is {num_units}"
            )
            ongoing_trip.clear_states()
            return

        if not num_units:
            raise ValueError(
                f"{ongoing_trip.sherpa_name} has reached a {station_type} station, no tote info available in trip metadata"
            )

        ongoing_trip.add_state(conveyor_start_state)
        conveyor_send_msg = rqm.PeripheralsReq(
            conveyor=rqm.ConveyorReq(direction=direction, num_units=num_units)
        )
        _ = utils_comms.send_req_to_sherpa(self.dbsession, sherpa, conveyor_send_msg)

    def do_post_actions(
        self, ongoing_trip: tm.OngoingTrip, sherpa: fm.Sherpa, curr_station: fm.Station
    ):

        if not curr_station:
            raise ValueError("Sherpa not at a station, cannot do post action")

        logging.getLogger(sherpa.name).info(
            f"{sherpa.name} reached a station {curr_station.name} with properties {curr_station.properties}"
        )

        if StationProperties.AUTO_HITCH in curr_station.properties:
            self.add_auto_hitch_start_to_ongoing_trip(ongoing_trip, sherpa)

        if StationProperties.AUTO_UNHITCH in curr_station.properties:
            self.add_auto_unhitch_start_to_ongoing_trip(ongoing_trip, sherpa)

        if StationProperties.DISPATCH_NOT_REQD not in curr_station.properties:
            timeout = StationProperties.DISPATCH_OPTIONAL in curr_station.properties
            self.add_dispatch_start_to_ongoing_trip(ongoing_trip, sherpa, timeout)
            if StationProperties.DISPATCH_OPTIONAL in curr_station.properties:
                log_level = mm.NotificationLevels.info
            else:
                log_level = mm.NotificationLevels.action_request

            self.dbsession.add_notification(
                [sherpa.name, sherpa.fleet.name, sherpa.fleet.customer],
                f"Need a dispatch button press on {sherpa.name} which is parked at {curr_station.name}",
                log_level,
                mm.NotificationModules.dispatch_button,
            )

        if any(
            prop in curr_station.properties
            for prop in [StationProperties.CONVEYOR, StationProperties.CHUTE]
        ):
            logging.getLogger(sherpa.name).info(
                f"{sherpa.name} reached a conveyor/chute station"
            )
            self.add_conveyor_start_to_ongoing_trip(ongoing_trip, sherpa, curr_station)

    def resolve_auto_hitch_error(
        self,
        ongoing_trip: tm.OngoingTrip,
        sherpa: fm.Sherpa,
        curr_station: fm.Station,
        req: rqm.SherpaPeripheralsReq,
    ):
        sherpa_name = req.source
        peripheral_info = req.auto_hitch

        # AUTO UNHITCH
        if not peripheral_info.hitch:
            if tm.TripState.WAITING_STATION_AUTO_UNHITCH_START in ongoing_trip.states:
                ongoing_trip.add_state(tm.TripState.WAITING_STATION_AUTO_UNHITCH_END)
                peripheral_msg = f"Resolving {req.error_device} error for {sherpa_name}, will wait for dispatch button press to continue"
                logging.getLogger().warning(peripheral_msg)
                self.add_dispatch_start_to_ongoing_trip(ongoing_trip, sherpa)
                self.dbsession.add_notification(
                    [sherpa.name, sherpa.fleet.name, sherpa.fleet.customer],
                    peripheral_msg,
                    mm.NotificationLevels.action_request,
                    mm.NotificationModules.trolley,
                )

            else:
                logging.getLogger().info(
                    f"Ignoring {req.error_device} error message from {sherpa_name}"
                )

        if peripheral_info.hitch:
            logging.getLogger().info(
                f"Cannot resolve {req.error_device} error for {sherpa_name}, {req}"
            )

    def resolve_conveyor_error(
        self,
        ongoing_trip: tm.OngoingTrip,
        sherpa: fm.Sherpa,
        curr_station: fm.Station,
        req: rqm.SherpaPeripheralsReq,
    ):
        sherpa_name = req.source
        direction = req.conveyor.direction

        conveyor_start_state = getattr(
            tm.TripState, f"WAITING_STATION_CONV_{direction.upper()}_START"
        )
        conveyor_end_state = getattr(
            tm.TripState, f"WAITING_STATION_CONV_{direction.upper()}_END"
        )

        if conveyor_start_state in ongoing_trip.states:
            num_units = hutils.get_conveyor_ops_info(ongoing_trip.trip.trip_metadata)
            ongoing_trip.add_state(conveyor_end_state)

            if direction == "send":
                peripheral_msg = f"Resolving {req.error_device} error for {sherpa_name}, transfer all the totes on the mule to the chute and press dispatch button"
            else:
                peripheral_msg = f"Resolving {req.error_device} error for {sherpa_name}, move {num_units} tote(s) to the mule from the conveyor and press dispatch button"

            logging.getLogger().info(peripheral_msg)
            self.dbsession.add_notification(
                [sherpa.name, sherpa.fleet.name, sherpa.fleet.customer],
                peripheral_msg,
                mm.NotificationLevels.action_request,
                mm.NotificationModules.conveyor,
            )
            self.add_dispatch_start_to_ongoing_trip(ongoing_trip, sherpa)
        else:
            logging.getLogger().info(
                f"Ignoring {req.error_device} error message from {sherpa_name}"
            )

    def delete_ongoing_trip(
        self,
        all_ongoing_trips: List[tm.OngoingTrip],
        all_sherpas: List[fm.Sherpa],
        all_trip_analytics: List[tm.TripAnalytics],
        force_delete=False,
    ):
        for ongoing_trip, sherpa, trip_analytics in zip(
            all_ongoing_trips, all_sherpas, all_trip_analytics
        ):
            logging.getLogger().info(
                f"Will try to deleting ongoing trip trip_id: {ongoing_trip.trip.id} booking_id: {ongoing_trip.trip.booking_id}"
            )

            if trip_analytics:
                trip_analytics.end_time = datetime.datetime.now()

            self.end_trip(ongoing_trip, sherpa, False)

            # add fleet_names to req_ctxt - this is for optimal_dispatch
            fleet_name = ongoing_trip.trip.fleet_name
            if fleet_name not in req_ctxt.fleet_names:
                req_ctxt.fleet_names.append(fleet_name)

            ongoing_trip.trip.cancel()

            if not force_delete:
                terminate_trip_msg = rqm.TerminateTripReq(
                    trip_id=ongoing_trip.trip_id, trip_leg_id=ongoing_trip.trip_leg_id
                )

                _ = utils_comms.send_req_to_sherpa(
                    self.dbsession, sherpa, terminate_trip_msg
                )
            else:
                logging.getLogger().info(
                    f"Not sending terminate_trip request to {sherpa.name}"
                )

            logging.getLogger().info(
                f"Deleted ongoing trip successfully trip_id: {ongoing_trip.trip.id} booking_id: {ongoing_trip.trip.booking_id}"
            )
        return {}

    def should_assign_next_task(
        self, sherpa: fm.Sherpa, ongoing_trip: tm.OngoingTrip, pending_trip: tm.PendingTrip
    ):

        done = False
        next_task = "no new task to assign"
        sherpa_status: fm.SherpaStatus = sherpa.status

        if not ongoing_trip and pending_trip:
            done = True
            next_task = "assign_new_trip"

        if ongoing_trip:
            """
            dbsession.session.commit() called in
            handle_sherpa_status refreshes ongoing_trip object,
            below code block can cause ObjectDeletedError, StaleDataError if ongoing_trip was deleted by a different rq job
            ongoing_trip is accessed by multiple handlers, added try block to resolve this
            """
            try:
                if ongoing_trip.finished():
                    done = True
                    next_task = "end_ongoing_trip"

                elif (
                    self.check_continue_curr_leg(ongoing_trip)
                    and ongoing_trip.check_continue()
                    and sherpa_status.continue_curr_task
                ):
                    done = True
                    next_task = "continue_leg"

                elif (
                    self.check_start_new_leg(ongoing_trip)
                    and not ongoing_trip.finished_booked()
                    and ongoing_trip.check_continue()
                ):
                    done = True
                    next_task = "start_leg"

            except Exception as e:
                logging.getLogger().warning(
                    f"unable to process ongoing_trip object for {sherpa.name}, Exception: {e}"
                )

        else:
            sherpa_status.continue_curr_task = False

        if next_task == "no new task to assign":
            logging.getLogger("status_updates").info(f"{sherpa.name} not assigned new task")

        if done and sherpa_status.disabled is True:
            logging.getLogger("status_updates").info(
                f"cannot assign new task to {sherpa.name}, sherpa is disabled, disabled_reason: {sherpa_status.disabled_reason}"
            )
            done = False
            sherpa_status.assign_next_task = False
        elif done:
            sherpa_status.assign_next_task = True
        else:
            sherpa_status.assign_next_task = False

        return done, next_task

    def release_visas(self, visas_to_release, sherpa, notify=False):

        # update db
        for ezone in set(visas_to_release):
            utils_visa.unlock_exclusion_zone(self.dbsession, ezone, sherpa)
            visa_log = f"{sherpa.name} released {ezone.zone_id} visa"
            logging.getLogger("visa").info(visa_log)

            if notify is True:
                utils_util.maybe_add_notification(
                    self.dbsession,
                    [sherpa.name, sherpa.fleet.name, sherpa.fleet.customer],
                    visa_log,
                    mm.NotificationLevels.info,
                    mm.NotificationModules.visa,
                )

    def handle_book(self, req: rqm.BookingReq):
        response = {}
        for trip_msg in req.trips:
            booking_id = self.dbsession.get_new_booking_id()
            all_stations: List[fm.Station] = []

            if len(trip_msg.route) == 0:
                raise ValueError("Cannot book trip with no route")

            for station_name in trip_msg.route:
                try:
                    station = self.dbsession.get_station(station_name)
                except Exception as e:
                    invalid_station_error = f"Cannot accept the booking, invalid station ({station_name}) in the route"
                    invalid_station_error_e = invalid_station_error + f", expception: {e}"
                    logging.getLogger().error(invalid_station_error_e)
                    raise ValueError(invalid_station_error)

                all_stations.append(station)

            fleet_name = self.dbsession.get_fleet_name_from_route(trip_msg.route)

            # add fleet_names to req_ctxt - this is for optimal_dispatch
            if fleet_name not in req_ctxt.fleet_names:
                req_ctxt.fleet_names.append(fleet_name)

            self.check_if_booking_is_valid(trip_msg, all_stations)

            if not trip_msg.priority:
                trip_msg.priority = 1.0

            # add source of booking
            if trip_msg.metadata is None:
                trip_msg.metadata = {}

            booked_by = req.source

            trip: tm.Trip = self.dbsession.create_trip(
                trip_msg.route,
                trip_msg.priority,
                trip_msg.metadata,
                booking_id,
                fleet_name,
                booked_by,
            )
            self.dbsession.create_pending_trip(trip.id)
            response.update(
                {trip.id: {"booking_id": trip.booking_id, "status": trip.status}}
            )
            logging.getLogger().info(
                f"Created a pending trip : trip_id: {trip.id}, booking_id: {trip.booking_id}"
            )

        return response

    def handle_delete_booked_trip(self, req: rqm.DeleteBookedTripReq):
        response = {}

        # query db
        if req.trip_id is None:
            trips: List[tm.Trip] = self.dbsession.get_trip_with_booking_id(req.booking_id)
        else:
            trip: tm.Trip = self.dbsession.get_trip(req.trip_id)
            trips: List[tm.Trip] = [trip]

        all_to_be_cancelled_trips: List[tm.Trip] = []
        all_pending_trips: List[tm.PendingTrip] = []

        for trip in trips:
            if trip.status in tm.YET_TO_START_TRIP_STATUS:
                pending_trip: tm.PendingTrip = self.dbsession.get_pending_trip_with_trip_id(
                    trip.id
                )

                # add fleet_names to req_ctxt - this is for optimal_dispatch
                fleet_name = trip.fleet_name
                if fleet_name not in req_ctxt.fleet_names:
                    req_ctxt.fleet_names.append(fleet_name)

                all_pending_trips.append(pending_trip)
                all_to_be_cancelled_trips.append(trip)

        # end transaction
        self.dbsession.session.commit()

        # update db
        if len(all_to_be_cancelled_trips) == 0:
            raise ValueError(
                f"No Booked Trips to be Cancelled for booking_id: {req.booking_id}"
            )

        for trip, pending_trip in zip(all_to_be_cancelled_trips, all_pending_trips):
            self.dbsession.delete_pending_trip(pending_trip)
            trip.status = tm.TripStatus.CANCELLED
            logging.getLogger().info(
                f"Successfully deleted booked trip trip_id: {trip.id}, booking_id: {trip.booking_id}"
            )

        return response

    def handle_delete_ongoing_trip(self, req: rqm.DeleteOngoingTripReq):

        # query db
        if req.trip_id is None:
            trips: List[tm.Trip] = self.dbsession.get_trip_with_booking_id(req.booking_id)
        else:
            trip: tm.Trip = self.dbsession.get_trip(req.trip_id)
            trips: List[tm.Trip] = [trip]

        all_ongoing_trips: List[tm.OngoingTrip] = []
        all_sherpas: List[fm.Sherpa] = []
        all_trip_analytics: List[tm.TripAnalytics] = []

        reasons = {}
        for trip in trips:
            ongoing_trip: tm.OngoingTrip = self.dbsession.get_ongoing_trip_with_trip_id(
                trip.id
            )
            if ongoing_trip is not None:
                sherpa: fm.Sherpa = self.dbsession.get_sherpa(ongoing_trip.sherpa_name)
                trip_analytics = self.dbsession.get_trip_analytics(ongoing_trip.trip_leg_id)
                if sherpa.status.disabled_reason == cc.DisabledReason.STALE_HEARTBEAT:
                    sherpa_not_connected_warning = f"Cannot delete ongoing_trip {ongoing_trip.trip_id}, sherpa: {ongoing_trip.sherpa_name} not connected"
                    logging.getLogger().warning(sherpa_not_connected_warning)
                    reasons.update({trip.id: sherpa_not_connected_warning})
                else:
                    all_trip_analytics.append(trip_analytics)
                    all_ongoing_trips.append(ongoing_trip)
                    all_sherpas.append(sherpa)

        # end transaction
        self.dbsession.session.commit()

        # update db
        if len(all_ongoing_trips) == 0:
            raise ValueError(
                f"Couldn't delete ongoing_trips for booking_id: {req.booking_id}, reasons: {reasons}"
            )
        response = self.delete_ongoing_trip(
            all_ongoing_trips, all_sherpas, all_trip_analytics
        )

        return response

    def handle_force_delete_ongoing_trip(self, req: rqm.ForceDeleteOngoingTripReq):
        response = {}

        all_trip_analytics = []
        all_ongoing_trips = []
        all_sherpas = []

        # query db
        sherpa: fm.Sherpa = self.dbsession.get_sherpa(req.sherpa_name)

        if sherpa.status.trip_id is None:
            raise ValueError("Sherpa has no ongoing_trip")

        ongoing_trip: tm.OngoingTrip = self.dbsession.get_ongoing_trip_with_trip_id(
            sherpa.status.trip_id
        )

        if ongoing_trip is None:
            raise ValueError("Sherpa has no ongoing_trip")

        trip_analytics = self.dbsession.get_trip_analytics(ongoing_trip.trip_leg_id)

        all_trip_analytics.append(trip_analytics)
        all_ongoing_trips.append(ongoing_trip)
        all_sherpas.append(sherpa)

        # end transaction
        self.dbsession.session.commit()

        # update db
        response = self.delete_ongoing_trip(
            all_ongoing_trips, all_sherpas, all_trip_analytics, force_delete=True
        )

        return response

    def handle_sherpa_status(self, req: rqm.SherpaStatusMsg):

        # query db
        sherpa, ongoing_trip, pending_trip = self.get_sherpa_trips(req.sherpa_name)
        status: fm.SherpaStatus = sherpa.status

        if req.mode != status.mode:
            last_sherpa_mode_change = self.dbsession.get_last_sherpa_mode_change(
                req.sherpa_name
            )

        # end transaction
        self.dbsession.session.commit()

        # update db
        status.pose = req.current_pose

        if sherpa.parking_id is not None:
            if not utils_util.are_poses_close(status.pose, sherpa.parked_at.pose):
                logging.getLogger("status_updates").warning(
                    f"Setting {sherpa.name} parking_id to None, sherpa pose not matching {sherpa.parking_id}"
                )
                sherpa.parking_id = None

        status.battery_status = req.battery_status
        status.error = req.error_info if req.error else None

        if status.disabled and status.disabled_reason == cc.DisabledReason.STALE_HEARTBEAT:
            status.disabled = False
            status.disabled_reason = None

        if req.mode != "fleet":
            logging.getLogger("status_updates").info(f"{sherpa.name} uninitialized")
            status.initialized = False
            status.continue_curr_task = False

        elif not status.initialized:
            # sherpa switched to fleet mode
            self.initialize_sherpa(sherpa)

        if req.mode == "error":
            sherpa_error_alert = f"{req.sherpa_name} in error mode"
            utils_util.maybe_add_notification(
                self.dbsession,
                [sherpa.name, sherpa.fleet.name, sherpa.fleet.customer],
                sherpa_error_alert,
                mm.NotificationLevels.alert,
                mm.NotificationModules.errors,
            )

        _, _ = self.should_assign_next_task(sherpa, ongoing_trip, pending_trip)

        if req.mode == status.mode:
            return

        init_req: rqm.InitReq = rqm.InitReq()
        init_response = utils_comms.send_req_to_sherpa(self.dbsession, sherpa, init_req)
        self.update_sherpa_info(status, init_response)

        status.mode = req.mode

        hutils.record_sherpa_mode_change(
            self.dbsession, sherpa.name, req.mode, last_sherpa_mode_change
        )

        logging.getLogger(sherpa.name).info(f"{sherpa.name} switched to {req.mode} mode")

    def handle_trip_status(self, req: rqm.TripStatusMsg):

        # query db
        sherpa: fm.Sherpa = self.dbsession.get_sherpa(req.source)
        ongoing_trip: tm.OngoingTrip = self.dbsession.get_ongoing_trip_with_trip_id(
            req.trip_id
        )

        if not ongoing_trip:
            logging.getLogger("status_updates").info(
                f"Trip status sent by {sherpa.name} is invalid/delayed no ongoing trip data found trip_id: {req.trip_id}"
            )
            return

        trip_analytics = self.dbsession.get_trip_analytics(ongoing_trip.trip_leg_id)

        if req.trip_leg_id != ongoing_trip.trip_leg_id:
            logging.getLogger("status_updates").info(
                f"Trip status sent by {sherpa.name} is invalid sherpa_trip_leg_id: {req.trip_leg_id} FM_trip_leg_id: {ongoing_trip.trip_leg_id}"
            )
            return

        if not ongoing_trip.next_station():
            logging.getLogger("status_updates").info(
                f"Trip status sent by {sherpa.name} is delayed all trip legs completed trip_id: {req.trip_id}"
            )
            return

        # end transaction
        self.dbsession.session.commit()

        # update db
        ongoing_trip.trip.update_etas(float(req.trip_info.eta), ongoing_trip.next_idx_aug)

        if req.stoppages.extra_info.velocity_speed_factor < 0.1:
            ongoing_trip.trip_leg.status = tm.TripLegStatus.STOPPED
            ongoing_trip.trip_leg.stoppage_reason = req.stoppages.type
            if req.stoppages.type == "waiting for dispatch button":
                dispatch_button_stoppage = (
                    f"{sherpa.name} waiting for dispatch button press"
                )
                utils_util.maybe_add_notification(
                    self.dbsession,
                    [sherpa.name, sherpa.fleet.name, sherpa.fleet.customer],
                    dispatch_button_stoppage,
                    mm.NotificationLevels.action_request,
                    mm.NotificationModules.dispatch_button,
                )

        elif req.stoppages.extra_info.velocity_speed_factor < 0.9:
            ongoing_trip.trip_leg.status = tm.TripLegStatus.MOVING_SLOW
            ongoing_trip.trip_leg.stoppage_reason = None

        else:
            ongoing_trip.trip_leg.status = tm.TripLegStatus.MOVING
            ongoing_trip.trip_leg.stoppage_reason = None

        if trip_analytics:
            trip_analytics.cte = req.trip_info.cte
            trip_analytics.te = req.trip_info.te
            trip_analytics.progress = req.trip_info.progress
            trip_analytics.time_elapsed_visa_stoppages = (
                req.stoppages.extra_info.time_elapsed_visa_stoppages
            )
            trip_analytics.time_elapsed_obstacle_stoppages = (
                req.stoppages.extra_info.time_elapsed_obstacle_stoppages
            )
            trip_analytics.time_elapsed_other_stoppages = (
                req.stoppages.extra_info.time_elapsed_other_stoppages
            )
            trip_analytics.num_trip_msg = trip_analytics.num_trip_msg + 1

        else:
            trip_analytics: tm.TripAnalytics = tm.TripAnalytics(
                sherpa_name=sherpa.name,
                trip_id=ongoing_trip.trip_id,
                trip_leg_id=ongoing_trip.trip_leg_id,
                start_time=ongoing_trip.trip_leg.start_time,
                from_station=ongoing_trip.trip_leg.from_station,
                to_station=ongoing_trip.trip_leg.to_station,
                expected_trip_time=ongoing_trip.trip.etas_at_start[
                    ongoing_trip.next_idx_aug
                ],
                progress=0.0,
                route_length=ongoing_trip.trip.route_lengths[ongoing_trip.next_idx_aug],
                actual_trip_time=None,
                cte=req.trip_info.cte,
                te=req.trip_info.te,
                time_elapsed_visa_stoppages=req.stoppages.extra_info.time_elapsed_visa_stoppages,
                time_elapsed_obstacle_stoppages=req.stoppages.extra_info.time_elapsed_obstacle_stoppages,
                time_elapsed_other_stoppages=req.stoppages.extra_info.time_elapsed_other_stoppages,
                num_trip_msg=1,
            )
            self.dbsession.add_to_session(trip_analytics)
            logging.getLogger("status_updates").info(
                f"added TripAnalytics entry for trip_leg_id: {ongoing_trip.trip_leg_id}"
            )

    def handle_trigger_optimal_dispatch(self, req: rqm.TriggerOptimalDispatch):

        fleet_name = req.fleet_name
        # add fleet_names to req_ctxt - this is for optimal_dispatch
        if fleet_name not in req_ctxt.fleet_names:
            req_ctxt.fleet_names.append(fleet_name)

        self.run_optimal_dispatch(req_ctxt.fleet_names)

    def handle_assign_next_task(self, req: rqm.AssignNextTask):

        # query db
        sherpa, ongoing_trip, pending_trip = self.get_sherpa_trips(req.sherpa_name)

        all_stations: List[fm.Station] = []
        if pending_trip:
            for station_name in pending_trip.trip.augmented_route:
                try:
                    station: fm.Station = self.dbsession.get_station(station_name)
                    all_stations.append(station)
                except Exception as e:
                    trip_error_msg = f"Cancel the trip: {pending_trip.trip_id}, invalid station ({station_name}) in the trip route"
                    trip_error_msg_e = trip_error_msg + f", exception: {e}"
                    logging.getLogger().warning(trip_error_msg_e)
                    utils_util.maybe_add_notification(
                        self.dbsession,
                        [sherpa.name, sherpa.fleet.name, sherpa.fleet.customer],
                        trip_error_msg,
                        mm.NotificationLevels.alert,
                        mm.NotificationModules.errors,
                    )
                    return

        if ongoing_trip:
            from_station = None
            to_station = None
            curr_station = ongoing_trip.curr_station()
            next_station = ongoing_trip.next_station()
            if curr_station:
                from_station: fm.Station = self.dbsession.get_station(curr_station)
            if next_station:
                to_station: fm.Station = self.dbsession.get_station(next_station)

        # setting assign_next_task to make sure handle_assign_next_task is not called repeatedly
        sherpa.status.assign_next_task = False

        # end transaction
        self.dbsession.session.commit()

        # update db
        valid_tasks = ["assign_new_trip", "end_ongoing_trip", "continue_leg", "start_leg"]
        done, next_task = self.should_assign_next_task(sherpa, ongoing_trip, pending_trip)
        sherpa.status.assign_next_task = False

        if done and next_task in valid_tasks:
            if next_task == "assign_new_trip":
                logging.getLogger("status_updates").info(
                    f"will try to assign a new trip for {sherpa.name}, ongoing completed"
                )
                self.assign_new_trip(sherpa, pending_trip, all_stations)
                return

            if not ongoing_trip:
                raise ValueError(
                    f"No ongoing trip, {sherpa.name}, next_task: {done, next_task}"
                )

            if next_task == "end_ongoing_trip":
                self.end_trip(ongoing_trip, sherpa, True)

                fleet_name = ongoing_trip.trip.fleet_name
                # add fleet_names to req_ctxt - this is for optimal_dispatch
                if fleet_name not in req_ctxt.fleet_names:
                    req_ctxt.fleet_names.append(fleet_name)

                self.run_optimal_dispatch(req_ctxt.fleet_names)

            if next_task == "continue_leg":
                logging.getLogger(sherpa.name).info(f"{sherpa.name} continuing leg")
                self.continue_leg(ongoing_trip, sherpa, from_station, to_station)

            elif next_task == "start_leg":
                logging.getLogger(sherpa.name).info(f"{sherpa.name} starting new leg")
                self.start_leg(ongoing_trip, sherpa, from_station, to_station)

    def handle_reached(self, req: rqm.ReachedReq):

        # query db
        sherpa: fm.Sherpa = self.dbsession.get_sherpa(req.source)
        ongoing_trip: tm.OngoingTrip = self.dbsession.get_ongoing_trip(sherpa.name)

        if (
            ongoing_trip.trip_leg_id != req.trip_leg_id
            or ongoing_trip.trip_id != req.trip_id
        ):
            raise ValueError(
                f"Trip information mismatch(trip_id: {req.trip_id} trip_leg_id: {req.trip_leg_id}) ongoing_trip_id: {ongoing_trip.trip_id} ongoing_trip_leg_id: {ongoing_trip.trip_leg_id}"
            )

        curr_station: fm.Station = self.dbsession.get_station(ongoing_trip.next_station())

        if not utils_util.are_poses_close(curr_station.pose, req.destination_pose):
            raise ValueError(
                f"{sherpa.name} was sent to {curr_station.pose} but reached {req.destination_pose}"
            )

        trip_analytics: tm.TripAnalytics = self.dbsession.get_trip_analytics(
            ongoing_trip.trip_leg_id
        )

        # end transaction
        self.dbsession.session.commit()

        # update db
        sherpa.pose = req.destination_pose
        sherpa.parking_id = curr_station.name
        self.end_leg(ongoing_trip, sherpa, curr_station, trip_analytics)

    def handle_induct_sherpa(self, req: rqm.SherpaInductReq):
        response = {}
        # query db
        sherpa: fm.Sherpa = self.dbsession.get_sherpa(req.sherpa_name)

        if sherpa.status.pose is None:
            raise ValueError(
                f"{sherpa.name} cannot be inducted for doing trips sherpa pose information is not available with fleet manager",
            )

        sherpa_availability = self.dbsession.get_sherpa_availability(sherpa.name)

        # end transaction
        self.dbsession.session.commit()

        # update db
        if not req.induct:
            self.release_visas(sherpa.exclusion_zones, sherpa, notify=True)
            sherpa.parking_id = None
        else:
            reset_visas_held_req = rqm.ResetVisasHeldReq()
            _ = utils_comms.send_req_to_sherpa(self.dbsession, sherpa, reset_visas_held_req)

        fleet_name = sherpa.fleet.name
        # add fleet_names to req_ctxt - this is for optimal_dispatch
        if fleet_name not in req_ctxt.fleet_names:
            req_ctxt.fleet_names.append(fleet_name)

        sherpa.status.inducted = req.induct
        sherpa_availability.available = req.induct

        return response

    def handle_peripherals(self, req: rqm.SherpaPeripheralsReq):

        # query db
        sherpa: fm.Sherpa = self.dbsession.get_sherpa(req.source)
        ongoing_trip: tm.OngoingTrip = self.dbsession.get_ongoing_trip(sherpa.name)
        curr_station = None
        if ongoing_trip:
            if ongoing_trip.curr_station():
                curr_station: fm.Station = self.dbsession.get_station(
                    ongoing_trip.curr_station()
                )

        # end transaction
        self.dbsession.session.commit()

        # update db
        if not ongoing_trip:
            logging.getLogger(sherpa.name).info(
                f"ignoring peripherals request from {sherpa.name} without ongoing trip"
            )
            return

        if req.error_device:
            self.handle_peripheral_error(ongoing_trip, sherpa, curr_station, req)
            return

        if req.dispatch_button:
            self.handle_dispatch_button(
                ongoing_trip, sherpa, curr_station, req.dispatch_button
            )

        elif req.auto_hitch:
            self.handle_auto_hitch(ongoing_trip, sherpa, curr_station, req.auto_hitch)

        elif req.conveyor:
            conveyor_ack = req.conveyor.ack
            if conveyor_ack:
                self.handle_conveyor_ack(ongoing_trip, sherpa, curr_station, req.conveyor)
                return
            self.handle_conveyor(ongoing_trip, sherpa, curr_station, req.conveyor)

    def handle_peripheral_error(
        self,
        ongoing_trip: tm.OngoingTrip,
        sherpa: fm.Sherpa,
        curr_station: fm.Station,
        req: rqm.SherpaPeripheralsReq,
    ):

        valid_error_devices = ["auto_hitch", "conveyor"]
        if req.error_device in valid_error_devices:
            peripheral_error_resolver = getattr(
                self, f"resolve_{req.error_device}_error", None
            )
            peripheral_info = getattr(req, req.error_device, None)
            if peripheral_info is not None and peripheral_error_resolver is not None:
                peripheral_error_resolver(ongoing_trip, sherpa, curr_station, req)
            else:
                raise ValueError(f"Unable to resolve {req.error_device} peripheral error")
        else:
            raise ValueError(f" {req.error_device} peripheral error can't be handled")

    def handle_dispatch_button(
        self,
        ongoing_trip: tm.OngoingTrip,
        sherpa: fm.Sherpa,
        curr_station: fm.Station,
        req: rqm.DispatchButtonReq,
    ):

        if not req.value:
            logging.getLogger(sherpa.name).info(
                f"dispatch button not pressed on {sherpa.name}, taking no action"
            )
            return

        if tm.TripState.WAITING_STATION_DISPATCH_START not in ongoing_trip.states:
            logging.getLogger(sherpa.name).warning(
                f"ignoring dispatch button press on {sherpa.name}"
            )
            return

        ongoing_trip.add_state(tm.TripState.WAITING_STATION_DISPATCH_END)
        self.record_dispatch_wait_end(ongoing_trip)

        logging.getLogger(sherpa.name).info(f"dispatch button pressed on {sherpa.name}")

        # ask sherpa to stop playing the sound
        sound_msg = rqm.PeripheralsReq(
            speaker=rqm.SpeakerReq(sound=rqm.SoundEnum.wait_for_dispatch, play=False),
            indicator=rqm.IndicatorReq(pattern=rqm.PatternEnum.free, activate=True),
        )

        _ = utils_comms.send_req_to_sherpa(self.dbsession, sherpa, sound_msg)

    def handle_auto_hitch(
        self,
        ongoing_trip: tm.OngoingTrip,
        sherpa: fm.Sherpa,
        curr_station: fm.Station,
        req: rqm.HitchReq,
    ):

        # auto hitch
        if req.hitch:
            if tm.TripState.WAITING_STATION_AUTO_HITCH_START not in ongoing_trip.states:
                error = f"auto-hitch done by {sherpa.name} without auto-hitch command"
                logging.getLogger(sherpa.name).error(error)
                raise ValueError(error)

            ongoing_trip.add_state(tm.TripState.WAITING_STATION_AUTO_HITCH_END)
            logging.getLogger(sherpa.name).info(f"auto-hitch done by {sherpa.name}")

        # auto unhitch
        else:
            if tm.TripState.WAITING_STATION_AUTO_UNHITCH_START not in ongoing_trip.states:
                error = f"auto-unhitch done by {sherpa.name} without auto-unhitch command"
                logging.getLogger(sherpa.name).error(error)
                raise ValueError(error)

            ongoing_trip.add_state(tm.TripState.WAITING_STATION_AUTO_UNHITCH_END)
            logging.getLogger(sherpa.name).info(f"auto-unhitch done by {sherpa.name}")

    def handle_conveyor(
        self,
        ongoing_trip: tm.OngoingTrip,
        sherpa: fm.Sherpa,
        curr_station: fm.Station,
        req: rqm.ConveyorReq,
    ):
        conveyor_start_state = getattr(
            tm.TripState, f"WAITING_STATION_CONV_{req.direction.upper()}_START"
        )

        conveyor_end_state = getattr(
            tm.TripState, f"WAITING_STATION_CONV_{req.direction.upper()}_END"
        )

        if conveyor_start_state not in ongoing_trip.states:
            error = f"{sherpa.name} {req.direction} totes without conveyor {req.direction} command"
            raise ValueError(error)

        ongoing_trip.add_state(conveyor_end_state)
        logging.getLogger(sherpa.name).info(
            f"CONV_{req.direction.upper()} completed by {sherpa.name}"
        )

    def handle_conveyor_ack(
        self,
        ongoing_trip: tm.OngoingTrip,
        sherpa: fm.Sherpa,
        curr_station: fm.Station,
        req: rqm.ConveyorReq,
    ):

        conveyor_start_state = getattr(
            tm.TripState, f"WAITING_STATION_CONV_{req.direction.upper()}_START"
        )

        if conveyor_start_state not in ongoing_trip.states:
            error = f"{sherpa.name} sent a invalid conveyor ack message {ongoing_trip.states} doesn't match ack msg"
            raise ValueError(error)

        if StationProperties.CONVEYOR in curr_station.properties:
            transfer_tote_msg = f"will send msg to the conveyor at station: {curr_station.name} to transfer {req.num_units} tote(s)"
            logging.getLogger().info(transfer_tote_msg)

            if req.num_units == 2:
                msg_to_forward = "transfer_2totes"
            elif req.num_units == 1:
                msg_to_forward = "transfer_tote"

            utils_comms.send_msg_to_plugin(
                msg_to_forward, f"plugin_conveyor_{curr_station.name}"
            )

            self.dbsession.add_notification(
                [sherpa.name, curr_station.name, sherpa.fleet.name, sherpa.fleet.customer],
                transfer_tote_msg,
                mm.NotificationLevels.info,
                mm.NotificationModules.conveyor,
            )

    def handle_resource_access(self, req: rqm.ResourceReq):
        sherpa: fm.Sherpa = self.dbsession.get_sherpa(req.source)
        if not req.visa:
            logging.getLogger(sherpa.name).warning("requested access type not supported")
            return None
        return self.handle_visa_access(req.visa, req.access_type, sherpa)

    def handle_visa_access(
        self, req: rqm.VisaReq, access_type: rqm.AccessType, sherpa: fm.Sherpa
    ):
        # do not assign next destination after processing a visa request.
        if access_type == rqm.AccessType.REQUEST:
            return self.handle_visa_request(req, sherpa)
        elif access_type == rqm.AccessType.RELEASE:
            return self.handle_visa_release(req, sherpa)

    def handle_visa_request(self, req: rqm.VisaReq, sherpa: fm.Sherpa):
        # query db
        granted, reason, reqd_ezones = utils_visa.can_grant_visa(
            self.dbsession, sherpa, req
        )
        visa_rejects = self.dbsession.get_visa_rejects(reqd_ezones, sherpa.name)

        # end transaction
        self.dbsession.session.commit()

        # update db
        if not sherpa.status.inducted:
            granted = False
            reason = "sherpa disabled for trips"

        if granted:
            for ezone in set(reqd_ezones):
                utils_visa.lock_exclusion_zone(ezone, sherpa)
                if sherpa in ezone.waiting_sherpas:
                    ezone.waiting_sherpas.remove(sherpa)
        else:
            for ezone, visa_reject in zip(set(reqd_ezones), visa_rejects):
                if visa_reject is None:
                    vr = vm.VisaRejects(reason=reason)
                    vr.zone_id = ezone.zone_id
                    vr.sherpa_name = sherpa.name
                    self.dbsession.add_to_session(vr)
                else:
                    visa_reject.reason = reason

        granted_message = "granted" if granted else "not granted"
        visa_log = f"{sherpa.name} {granted_message} {req.visa_type} type visa to zone {req.zone_name}, reason: {reason}"
        logging.getLogger("visa").info(f"visa {granted_message} to {sherpa.name}")

        response: rqm.ResourceResp = rqm.ResourceResp(
            granted=granted, visa=req, access_type=rqm.AccessType.REQUEST
        )
        utils_util.maybe_add_notification(
            self.dbsession,
            [sherpa.name, sherpa.fleet.name, sherpa.fleet.customer],
            visa_log,
            mm.NotificationLevels.info,
            mm.NotificationModules.visa,
        )

        return response.to_json()

    def handle_visa_release(self, req: rqm.VisaReq, sherpa: fm.Sherpa):
        # query db
        visas_to_release = utils_visa.get_visas_to_release(self.dbsession, sherpa, req)

        # end transaction
        self.dbsession.session.commit()

        self.release_visas(visas_to_release, sherpa)

        response: rqm.ResourceResp = rqm.ResourceResp(
            granted=True, visa=req, access_type=rqm.AccessType.RELEASE
        )

        visa_log = f"{sherpa.name} released {req.visa_type} visa of zone {req.zone_name}"
        utils_util.maybe_add_notification(
            self.dbsession,
            [sherpa.name, sherpa.fleet.name, sherpa.fleet.customer],
            visa_log,
            mm.NotificationLevels.info,
            mm.NotificationModules.visa,
        )

        return response.to_json()

    def handle_sherpa_img_update(self, req: rqm.SherpaImgUpdateCtrlReq):
        response = {}
        # query db
        sherpa = self.dbsession.get_sherpa(req.sherpa_name)

        # end transaction
        self.dbsession.session.commit()

        # update db
        image_tag = "fm"
        fm_server_username = os.getenv("FM_SERVER_USERNAME")
        time_zone = os.getenv("PGTZ")
        image_update_req: rqm.SherpaImgUpdate = rqm.SherpaImgUpdate(
            image_tag=image_tag,
            fm_server_username=fm_server_username,
            time_zone=time_zone,
        )

        logging.getLogger().info(
            f"Sending request {image_update_req} to update docker image on {sherpa.name}"
        )
        utils_comms.send_req_to_sherpa(self.dbsession, sherpa, image_update_req)
        return response

    def handle_pass_to_sherpa(self, req):
        sherpa: fm.Sherpa = self.dbsession.get_sherpa(req.sherpa_name)

        # add fleet_names to req_ctxt - this is for optimal_dispatch
        fleet_name = sherpa.fleet.name
        if fleet_name not in req_ctxt.fleet_names:
            req_ctxt.fleet_names.append(fleet_name)

        logging.getLogger(sherpa.name).info(
            f"passing control request to sherpa {sherpa.name}, {req.dict()} "
        )

        if req.endpoint == rqm.PasstoSherpaEndpoints.RESET_POSE:
            if req.station_name is not None:
                sherpa.parking_id = req.station_name

        utils_comms.send_req_to_sherpa(self.dbsession, sherpa, req)

    def handle_save_route(self, req: rqm.SaveRouteReq):
        reponse = {}

        # query db
        saved_route = self.dbsession.get_saved_route(req.tag)

        stations = req.route

        for station_name in stations:
            try:
                _ = self.dbsession.get_station(station_name)
            except Exception as e:
                logging.getLogger().info(
                    f"unable to find station: {station_name}, Exception: {e}"
                )
                raise ValueError(f"{station_name} not found in DB, cannot add {req.route}")

        # end transaction
        self.dbsession.session.commit()

        # update db
        fleet_name = self.dbsession.get_fleet_name_from_route(req.route)

        if saved_route:
            can_edit = saved_route.other_info.get("can_edit", "False")

            if not eval(can_edit):
                raise ValueError("Cannot edit this route tag, can_edit is set to False")

            saved_route.route = req.route
            saved_route.fleet_name = fleet_name

            if req.other_info:
                saved_route.other_info.update(req.other_info)
                flag_modified(saved_route, "other_info")

            logging.getLogger().info(
                f"updated the route : {req.route} for the route tag : {req.tag} "
            )

        else:
            if req.other_info is None:
                req.other_info = {}

            if "can_edit" not in list(req.other_info.keys()):
                req.other_info["can_edit"] = "True"

            saved_route: tm.SaveRoute = tm.SavedRoutes(
                tag=req.tag,
                route=req.route,
                fleet_name=fleet_name,
                other_info=req.other_info,
            )

            self.dbsession.add_to_session(saved_route)
            logging.getLogger().info(
                f"Saved a new route : {req.route}, with tag : {req.tag} "
            )

        return reponse

    def handle(self, msg):
        self.dbsession = None
        init_request_context(msg)

        with DBSession() as dbsession:
            self.dbsession = dbsession

            if msg.type == cc.MessageType.FM_HEALTH_CHECK:
                self.run_health_check()
                return

            if msg.type == cc.MessageType.MISC_PROCESS:
                self.run_misc_processes()
                return

            # log, add msg to sherpa events
            self.record_msg_received(msg, cc.UpdateMsgs)
            handle_ok, reason = self.should_handle_msg(msg)

            if not handle_ok:
                self.ignore_msg(msg, cc.UpdateMsgs, reason)
                return

            # get handler
            msg_handler = getattr(self, "handle_" + msg.type, None)

            if not msg_handler:
                logging.getLogger().error(f"no handler defined for {msg.type}")
                return

            response = msg_handler(msg)

        # run optimal dispatch if needs be - need not be coupled with handler
        try:
            run_opt_d = False
            if msg.type in cc.OptimalDispatchInfluencers:
                run_opt_d = True
                if msg.type == cc.MessageType.PASS_TO_SHERPA:
                    if not isinstance(msg, rqm.ResetPoseReq):
                        run_opt_d = False
            if run_opt_d:
                with DBSession() as dbsession:
                    self.dbsession = dbsession
                    self.run_optimal_dispatch(req_ctxt.fleet_names)
        except Exception as e:
            logging.getLogger().error(f"couldn't run optimal dispatch, {e}")

        return response
