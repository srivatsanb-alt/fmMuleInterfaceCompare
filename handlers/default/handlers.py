import os
import datetime
from typing import List
from requests import Response
from sqlalchemy.orm.attributes import flag_modified

import models.fleet_models as fm
import models.misc_models as mm
import models.request_models as rqm
import models.trip_models as tm
import models.visa_models as vm
from models.base_models import StationProperties
from models.db_session import DBSession

import utils.comms as utils_comms
import utils.util as utils_util
import utils.visa_utils as utils_visa

from core.logs import get_logger
from core.constants import (
    FleetStatus,
    DisabledReason,
    MessageType,
    OptimalDispatchInfluencers,
    UpdateMsgs,
)
from core.config import Config

from optimal_dispatch.dispatcher import OptimalDispatch
import handlers.default.handler_utils as hutils


class RequestContext:
    msg_type: str
    sherpa_name: str
    logger = None


req_ctxt = RequestContext()


def init_request_context(req):
    req_ctxt.msg_type = req.type
    req_ctxt.source = req.source
    if isinstance(req, rqm.SherpaReq) or isinstance(req, rqm.SherpaMsg):
        req_ctxt.sherpa_name = req.source
        req_ctxt.source = req.source
    else:
        req_ctxt.sherpa_name = None

    # do not send a move to current destination, except if asked
    if isinstance(req, rqm.SherpaReq) or isinstance(req, rqm.SherpaMsg):
        req_ctxt.logger = get_logger(req.source)
    else:
        req_ctxt.logger = get_logger()


class Handlers:
    def should_handle_msg(self, msg):
        sherpa_name = req_ctxt.sherpa_name
        if not sherpa_name:
            return True, None

        sherpa: fm.Sherpa = self.dbsession.get_sherpa(sherpa_name)
        fleet: fm.Fleet = sherpa.fleet

        if fleet.status == FleetStatus.PAUSED:
            return False, f"fleet {fleet.name} is paused"

        return True, None

    def record_msg_received(self, msg, update_msgs):

        # add the message received to sherpa events
        if req_ctxt.sherpa_name and msg.type not in update_msgs:
            hutils.add_sherpa_event(
                self.dbsession, req_ctxt.sherpa_name, msg.type, "sent by sherpa"
            )

        if msg.type in update_msgs:
            get_logger("status_updates").info(f"{req_ctxt.sherpa_name} :  {msg}")
        else:
            get_logger().info(
                f"Got message of type {msg.type} from {req_ctxt.source} \n Message: {msg} \n"
            )

    def ignore_msg(self, msg, update_msgs, reason):
        if msg.type in update_msgs:
            get_logger("status_updates").warning(
                f"message of type {msg.type} ignored, reason={reason}"
            )
        else:
            get_logger().warning(f"message of type {msg.type} ignored, reason={reason}")

    def run_health_check(self):
        hutils.check_sherpa_status(self.dbsession)
        hutils.delete_notifications(self.dbsession)
        get_logger("status_updates").info("Ran a FM health check")

    def get_sherpa_trips(self, sherpa_name):
        sherpa: fm.Sherpa = self.dbsession.get_sherpa(sherpa_name)
        ongoing_trip: tm.OngoingTrip = self.dbsession.get_ongoing_trip(sherpa.name)
        pending_trip: tm.PendingTrip = self.dbsession.get_pending_trip(sherpa.name)
        return sherpa, ongoing_trip, pending_trip

    def initialize_sherpa(self, sherpa: fm.Sherpa):
        sherpa_status: fm.SherpaStatus = sherpa.status
        sherpa_status.initialized = True
        sherpa_status.idle = True
        sherpa_status.continue_curr_task = True
        get_logger(sherpa.name).info(f"{sherpa.name} initialized")

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

        if reason:
            raise ValueError(f"{reason}")

    def should_recreate_scheduled_trip(self, pending_trip: tm.PendingTrip):
        if not utils_util.check_if_timestamp_has_passed(pending_trip.trip.end_time):
            new_metadata = pending_trip.trip.trip_metadata
            time_period = new_metadata["scheduled_time_period"]
            new_start_time = datetime.datetime.now() + datetime.timedelta(
                seconds=int(time_period)
            )
            if new_start_time > pending_trip.trip.end_time:
                get_logger().info(
                    f"will not recreate trip {pending_trip.trip.id}, new trip start_time past scheduled_end_time"
                )
                return

            get_logger().info(
                f"recreating trip {pending_trip.trip.id}, scheduled trip needs to be continued"
            )

            new_start_time = utils_util.dt_to_str(new_start_time)
            new_metadata["scheduled_start_time"] = new_start_time
            get_logger().info(f"scheduled new metadata {new_metadata}")
            new_trip: tm.Trip = self.dbsession.create_trip(
                pending_trip.trip.route,
                pending_trip.trip.priority,
                new_metadata,
                pending_trip.trip.booking_id,
                pending_trip.trip.fleet_name,
            )
            self.dbsession.create_pending_trip(new_trip.id)
        else:
            get_logger().info(
                f"will not recreate trip {pending_trip.trip.id}, scheduled_end_time past current time"
            )

    def assign_new_trip(
        self,
        sherpa: fm.Sherpa,
        pending_trip: tm.PendingTrip,
        all_stations: List[fm.Station],
    ):
        fleet: fm.Fleet = sherpa.fleet

        if fleet.status == FleetStatus.STOPPED:
            get_logger(sherpa.name).info(
                f"fleet {fleet.name} is stopped, not assigning new trip to {sherpa.name}"
            )
            return False

        if not pending_trip:
            return False

        get_logger(sherpa.name).info(
            f"found pending trip id {pending_trip.trip_id}, route: {pending_trip.trip.route}"
        )

        sherpa_status: fm.SherpaStatus = sherpa.status
        sherpa_status.continue_curr_task = False

        if not hutils.is_sherpa_available_for_new_trip(sherpa_status):
            get_logger(sherpa.name).info(
                f"{sherpa.name} not available for {pending_trip.trip_id}"
            )
            return False

        if pending_trip.trip.scheduled:
            self.should_recreate_scheduled_trip(pending_trip)

        self.start_trip(pending_trip.trip, sherpa, all_stations)
        self.dbsession.delete_pending_trip(pending_trip)
        get_logger(sherpa.name).info(f"deleted pending trip id {pending_trip.trip_id}")
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
        get_logger(sherpa_name).info(f"trip {ongoing_trip.trip_id} finished")

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

        from_station_name = from_station.name if from_station else None
        started_leg_log = (
            f"{sherpa.name} started a trip leg of trip",
            f"(trip_id: {trip.id}) from",
            f"{from_station_name} to" "{to_station.name}",
        )

        get_logger(sherpa.name).info(started_leg_log)

        _: Response = utils_comms.send_move_msg(
            self.dbsession, sherpa, ongoing_trip, to_station
        )

        self.dbsession.add_notification(
            [sherpa.name, fleet.name],
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
        fleet_name = ongoing_trip.trip.fleet_name

        end_leg_log = f"{sherpa_name} finished a trip leg of trip (trip_id: {trip.id}) from {ongoing_trip.trip_leg.from_station} to {ongoing_trip.trip_leg.to_station}"
        get_logger(sherpa_name).info(end_leg_log)

        hutils.end_leg(ongoing_trip)

        if trip_analytics:
            trip_analytics.end_time = datetime.datetime.now()
            time_delta = datetime.datetime.now() - ongoing_trip.trip_leg.start_time
            trip_analytics.actual_trip_time = time_delta.seconds
            trip_analytics_log = (
                f"{sherpa_name} finished leg of trip {trip.id}",
                "trip_analytics:",
                f"{utils_util.get_table_as_dict(tm.TripAnalytics, trip_analytics)}",
            )
            get_logger(sherpa_name).info(trip_analytics_log)

        self.do_post_actions(ongoing_trip, sherpa, curr_station)
        self.dbsession.add_notification(
            [fleet_name, sherpa_name],
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

        get_logger(sherpa.name).info(
            f"{sherpa.name} continuing leg of trip {trip.id} from",
            f"{ongoing_trip.curr_station()} to {ongoing_trip.next_station()}",
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
    def run_optimal_dispatch(self):
        optimal_dispatch_config = Config.get_optimal_dispatch_config()
        optimal_dispatch = OptimalDispatch(optimal_dispatch_config)
        optimal_dispatch.run(self.dbsession)

    def do_pre_actions(self, ongoing_trip: tm.OngoingTrip):
        curr_station = ongoing_trip.curr_station()
        sherpa_name = ongoing_trip.sherpa_name
        if not curr_station:
            get_logger(sherpa_name).info(
                f"no pre-actions performed since {sherpa_name} is not at a trip station"
            )
            return

    def add_dispatch_start_to_ongoing_trip(
        self, ongoing_trip: tm.OngoingTrip, sherpa: fm.Sherpa, timeout=False
    ):
        ongoing_trip.add_state(tm.TripState.WAITING_STATION_DISPATCH_START)
        dispatch_mesg = rqm.DispatchButtonReq(value=True)
        if timeout:
            dispatch_timeout = Config.get_dispatch_timeout()
            dispatch_mesg = rqm.DispatchButtonReq(value=True, timeout=dispatch_timeout)

        sherpa_action_msg = rqm.PeripheralsReq(
            dispatch_button=dispatch_mesg,
            speaker=rqm.SpeakerReq(sound=rqm.SoundEnum.wait_for_dispatch, play=True),
            indicator=rqm.IndicatorReq(
                pattern=rqm.PatternEnum.wait_for_dispatch, activate=True
            ),
        )

        _ = utils_comms.send_msg_to_sherpa(self.dbsession, sherpa, sherpa_action_msg)

    def add_auto_hitch_start_to_ongoing_trip(
        self, ongoing_trip: tm.OngoingTrip, sherpa: fm.Sherpa
    ):
        ongoing_trip.add_state(tm.TripState.WAITING_STATION_AUTO_HITCH_START)
        hitch_msg = rqm.PeripheralsReq(auto_hitch=rqm.HitchReq(hitch=True))
        _ = utils_comms.send_msg_to_sherpa(self.dbsession, sherpa, hitch_msg)

    def add_auto_unhitch_start_to_ongoing_trip(
        self, ongoing_trip: tm.OngoingTrip, sherpa: fm.Sherpa
    ):
        ongoing_trip.add_state(tm.TripState.WAITING_STATION_AUTO_UNHITCH_START)
        unhitch_msg = rqm.PeripheralsReq(auto_hitch=rqm.HitchReq(hitch=False))
        _ = utils_comms.send_msg_to_sherpa(self.dbsession, sherpa, unhitch_msg)

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
        ongoing_trip.add_state(conveyor_start_state)

        if direction == "receive":
            num_units = utils_comms.get_num_units_converyor(station.name)
            # update metadata with num totes for dropping totes at chute
            trip_metadata = ongoing_trip.trip.trip_metadata
            trip_metadata["num_units"] = num_units
            flag_modified(ongoing_trip.trip, "trip_metadata")

        else:
            num_units = trip_metadata.get("num_units", None)
            if num_units is None:
                raise ValueError("No tote/units information present")

        if num_units == 0:
            get_logger().info(
                f"will not send conveyor msg to {ongoing_trip.sherpa_name}, reason: num_units is {num_units}"
            )
            return

        if not num_units:
            raise ValueError(
                f"{ongoing_trip.sherpa_name} has reached a {station_type} station, no tote info available in trip metadata"
            )
        conveyor_send_msg = rqm.PeripheralsReq(
            conveyor=rqm.ConveyorReq(direction=direction, num_units=num_units)
        )

        _ = utils_comms.send_msg_to_sherpa(self.dbsession, sherpa, conveyor_send_msg)

    def do_post_actions(
        self, ongoing_trip: tm.OngoingTrip, sherpa: fm.Sherpa, curr_station: fm.Station
    ):

        if not curr_station:
            raise ValueError("Sherpa not at a station, cannot do post action")

        get_logger(sherpa.name).info(
            f"{sherpa.name} reached a station {curr_station.name} with properties {curr_station.properties}"
        )

        if StationProperties.AUTO_HITCH in curr_station.properties:
            self.add_auto_hitch_start_to_ongoing_trip(ongoing_trip, sherpa)

        if StationProperties.AUTO_UNHITCH in curr_station.properties:
            self.add_auto_unhitch_start_to_ongoing_trip(ongoing_trip, sherpa)

        if StationProperties.DISPATCH_NOT_REQD not in curr_station.properties:
            timeout = StationProperties.DISPATCH_OPTIONAL in curr_station.properties
            self.add_dispatch_start_to_ongoing_trip(ongoing_trip, sherpa, timeout)

            self.dbsession.add_notification(
                [ongoing_trip.trip.fleet_name, sherpa.name],
                f"Need a dispatch button press on {sherpa.name} which is parked at {curr_station.name}",
                mm.NotificationLevels.action_request,
                mm.NotificationModules.peripheral_devices,
            )
        if any(
            prop in curr_station.properties
            for prop in [StationProperties.CONVEYOR, StationProperties.CHUTE]
        ):
            get_logger(sherpa.name).info(f"{sherpa.name} reached a conveyor/chute station")
            self.add_conveyor_start_to_ongoing_trip(ongoing_trip, sherpa, curr_station)

    def resolve_auto_hitch_error(
        self,
        ongoing_trip: tm.OngoingTrip,
        sherpa: fm.Sherpa,
        curr_station: fm.Station,
        req: rqm.SherpaPeripheralsReq,
    ):
        sherpa_name = req.source
        fleet_name = ongoing_trip.trip.fleet_name
        peripheral_info = req.auto_hitch

        # AUTO UNHITCH
        if not peripheral_info.hitch:
            if tm.TripState.WAITING_STATION_AUTO_UNHITCH_START in ongoing_trip.states:
                ongoing_trip.add_state(tm.TripState.WAITING_STATION_AUTO_UNHITCH_END)

                peripheral_msg = (
                    f"Resolving {req.error_device} error for",
                    f"{sherpa_name}, will wait for dispatch button",
                    "press to continue",
                )

                get_logger().warning(peripheral_msg)
                self.add_dispatch_start_to_ongoing_trip(ongoing_trip)
                self.dbsession.add_notification(
                    [fleet_name, sherpa_name],
                    peripheral_msg,
                    mm.NotificationLevels.action_request,
                    mm.NotificationModules.peripheral_devices,
                )

            else:
                get_logger().info(
                    f"Ignoring {req.error_device} error message from {sherpa_name}"
                )

        if peripheral_info.hitch:
            get_logger().info(
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
        fleet_name = ongoing_trip.trip.fleet_name
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
                peripheral_msg = (
                    f"Resolving {req.error_device} error for",
                    f"{sherpa_name},transfer all the totes on the",
                    "mule to the chute and press dispatch button",
                )
            else:
                peripheral_msg = (
                    f"Resolving {req.error_device} error for",
                    f"{sherpa_name},move {num_units} tote(s) to the",
                    f"mule and press dispatch button",
                )

            get_logger().info(peripheral_msg)
            self.dbsession.add_notification(
                [fleet_name, sherpa_name],
                peripheral_msg,
                mm.NotificationLevels.action_request,
                mm.NotificationModules.peripheral_devices,
            )
            self.add_dispatch_start_to_ongoing_trip(ongoing_trip)
        else:
            get_logger().info(
                f"Ignoring {req.error_device} error message from {sherpa_name}"
            )

    def delete_ongoing_trip(
        self,
        all_ongoing_trips: List[tm.OngoingTrip],
        all_sherpas: List[fm.Sherpa],
    ):
        for ongoing_trip, sherpa in zip(all_ongoing_trips, all_sherpas):
            get_logger().info(
                "Deleting ongoing trip",
                f"trip_id: {ongoing_trip.trip.id}",
                f"booking_id: {req.booking_id}",
            )
            self.end_trip(ongoing_trip, sherpa, False)
            ongoing_trip.trip.cancel()
            terminate_trip_msg = rqm.TerminateTripReq(
                trip_id=ongoing_trip.trip_id, trip_leg_id=ongoing_trip.trip_leg_id
            )
            _ = utils_comms.send_msg_to_sherpa(self.dbsession, sherpa, terminate_trip_msg)
            get_logger().info(
                "Deleted ongoing trip successfully",
                f"trip_id: {ongoing_trip.trip.id}",
                f"booking_id: {ongoing_trip.trip.booking_id}",
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
        else:
            sherpa_status.continue_curr_task = False

        if next_task == "no new task to assign":
            get_logger("status_updates").info(f"{sherpa.name} not assigned new task")

        if done:
            sherpa_status.assign_next_task = True
        else:
            sherpa_status.assign_next_task = False

        return done, next_task

    def handle_book(self, req: rqm.BookingReq):
        response = {}
        for trip_msg in req.trips:
            booking_id = self.dbsession.get_new_booking_id()
            fleet_name = self.dbsession.get_fleet_name_from_route(trip_msg.route)
            if fleet_name:
                # need priority for optimal dispatch logic, default is 1
                if not trip_msg.priority:
                    trip_msg.priority = 1.0

                all_stations: List[fm.Station] = []

                for station_name in trip_msg.route:
                    all_stations.append(self.dbsession.get_station(station_name))

                self.check_if_booking_is_valid(trip_msg, all_stations)

                trip: tm.Trip = self.dbsession.create_trip(
                    trip_msg.route,
                    trip_msg.priority,
                    trip_msg.metadata,
                    booking_id,
                    fleet_name,
                )
                self.dbsession.create_pending_trip(trip.id)
                response.update(
                    {trip.id: {"booking_id": trip.booking_id, "status": trip.status}}
                )
                get_logger().info(
                    f"Created a pending trip : trip_id: {trip.id}, booking_id: {trip.booking_id}"
                )

        return response

    def handle_delete_booked_trip(self, req: rqm.DeleteBookedTripReq):

        # query db
        trips: List[tm.Trip] = self.dbsession.get_trip_with_booking_id(req.booking_id)
        all_to_be_cancelled_trips = List[tm.Trip] = []
        all_pending_trips: List[tm.PendingTrip] = []

        for trip in trips:
            if trip.status in tm.YET_TO_START_TRIP_STATUS:
                pending_trip: tm.PendingTrip = self.dbsession.get_pending_trip_with_trip_id(
                    trip.id
                )
                all_pending_trips.append(pending_trip)
                all_to_be_cancelled_trips.append(trip)

        # end transaction
        self.dbsession.session.commit()

        # update db
        for trip, pending_trip in zip(all_to_be_cancelled_trips, all_pending_trips):
            self.dbsession.delete_pending_trip(pending_trip)
            trip.status = tm.TripStatus.CANCELLED
            get_logger().info(
                f"Successfully deleted booked trip",
                f"trip_id: {trip.id}, booking_id: {trip.booking_id}",
            )

    def handle_delete_ongoing_trip(self, req: rqm.DeleteOngoingTripReq):

        # query db
        trips: List[tm.Trip] = self.dbsession.get_trip_with_booking_id(req.booking_id)
        all_ongoing_trips: List[tm.OngoingTrip] = []
        all_sherpas: List[fm.Sherpa] = []

        for trip in trips:
            ongoing_trip: tm.OngoingTrip = self.dbsession.get_ongoing_trip_with_trip_id(
                trip.id
            )
            if ongoing_trip is not None:
                all_ongoing_trips.append(ongoing_trip)

            sherpa: fm.Sherpa = self.dbsession.get_sherpa(ongoing_trip.sherpa_name)
            all_sherpas.append(sherpa)

        # end transaction
        self.dbsession.session.commit()

        # update db
        response = self.delete_ongoing_trip(all_ongoing_trips, all_sherpas)
        return response

    def handle_sherpa_status(self, req: rqm.SherpaStatusMsg):

        # query db
        sherpa, ongoing_trip, pending_trip = self.get_sherpa_trips(req.sherpa_name)
        status: fm.SherpaStatus = sherpa.status

        # end transaction
        self.dbsession.session.commit()

        # update db
        status.pose = req.current_pose
        status.battery_status = req.battery_status
        status.error = req.error_info if req.error else None

        if status.disabled and status.disabled_reason == DisabledReason.STALE_HEARTBEAT:
            status.disabled = False
            status.disabled_reason = None

        if req.mode != "fleet":
            get_logger(sherpa.name).info(f"{sherpa.name} uninitialized")
            status.initialized = False
            status.continue_curr_task = False

        elif not status.initialized:
            # sherpa switched to fleet mode
            init_req: rqm.InitReq = rqm.InitReq()
            response: Response = utils_comms.get(sherpa, init_req)
            _: rqm.InitResp = rqm.InitResp.from_dict(response.json())
            self.initialize_sherpa(sherpa)

        _, _ = self.should_assign_next_task(sherpa, ongoing_trip, pending_trip)

        if req.mode == status.mode:
            return

        status.mode = req.mode
        get_logger(sherpa.name).info(f"{sherpa.name} switched to {req.mode} mode")

    def handle_trip_status(self, req: rqm.TripStatusMsg):

        # query db
        sherpa: fm.Sherpa = self.dbsession.get_sherpa(req.source)
        ongoing_trip: tm.OngoingTrip = self.dbsession.get_ongoing_trip_with_trip_id(
            req.trip_id
        )
        trip_analytics = self.dbsession.get_trip_analytics(ongoing_trip.trip_leg_id)

        if not ongoing_trip:
            get_logger().info(
                f"Trip status sent by {sherpa.name} is invalid/delayed",
                f"no ongoing trip data found trip_id: {req.trip_id}",
            )
            return

        if req.trip_leg_id != ongoing_trip.trip_leg_id:
            get_logger().info(
                f"Trip status sent by {sherpa.name} is invalid",
                f"sherpa_trip_leg_id: {req.trip_leg_id}",
                f"FM_trip_leg_id: {ongoing_trip.trip_leg_id}",
            )
            return

        if not ongoing_trip.next_station():
            get_logger().info(
                f"Trip status sent by {sherpa.name} is delayed",
                f"all trip legs completed trip_id: {req.trip_id}",
            )
            return

        # end transaction
        self.dbsession.session.commit()

        # update db
        ongoing_trip.trip.update_etas(float(req.trip_info.eta), ongoing_trip.next_idx_aug)

        if trip_analytics:
            trip_analytics.cte = req.trip_info.cte
            trip_analytics.te = req.trip_info.te
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
                actual_trip_time=None,
                cte=req.trip_info.cte,
                te=req.trip_info.te,
                time_elapsed_visa_stoppages=req.stoppages.extra_info.time_elapsed_visa_stoppages,
                time_elapsed_obstacle_stoppages=req.stoppages.extra_info.time_elapsed_obstacle_stoppages,
                time_elapsed_other_stoppages=req.stoppages.extra_info.time_elapsed_other_stoppages,
                num_trip_msg=1,
            )
            self.dbsession.add_to_session(trip_analytics)
            get_logger().info(
                f"added TripAnalytics entry for trip_leg_id: {ongoing_trip.trip_leg_id}"
            )

        trip_status_update = {}

        # send to frontend
        trip_status_update.update(
            {
                "type": "trip_status",
                "sherpa_name": sherpa.name,
                "fleet_name": sherpa.fleet.name,
            }
        )

        trip_status_update.update(
            utils_util.get_table_as_dict(tm.TripAnalytics, trip_analytics)
        )
        trip_status_update.update({"stoppages": {"type": req.stoppages.type}})
        utils_comms.send_status_update(trip_status_update)

    def handle_assign_next_task(self, req: rqm.AssignNextTask):

        # Run optimal dispatch for scheduled trips
        if req.sherpa_name is None:
            self.run_optimal_dispatch()
            return

        # query db
        sherpa, ongoing_trip, pending_trip = self.get_sherpa_trips(req.sherpa_name)

        all_stations: List[fm.Station] = []
        if pending_trip:
            for station_name in pending_trip.trip.augmented_route:
                station: fm.Station = self.dbsession.get_station(station_name)
                all_stations.append(station)

        if ongoing_trip:
            from_station = None
            to_station = None
            curr_station = ongoing_trip.curr_station()
            next_station = ongoing_trip.next_station()
            if curr_station:
                from_station: fm.Station = self.dbsession.get_station(curr_station)
            if next_station:
                to_station: fm.Station = self.dbsession.get_station(next_station)

        # end transaction
        self.dbsession.session.commit()

        # update db
        valid_tasks = ["assign_new_trip", "end_ongoing_trip", "continue_leg", "start_leg"]
        done, next_task = self.should_assign_next_task(sherpa, ongoing_trip, pending_trip)
        sherpa.status.assign_next_task = False

        if done and next_task in valid_tasks:
            if next_task == "assign_new_trip":
                get_logger("status_updates").info(
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
                self.run_optimal_dispatch()

            if next_task == "continue_leg":
                get_logger(sherpa.name).info(f"{sherpa.name} continuing leg")
                self.continue_leg(ongoing_trip, sherpa, from_station, to_station)

            elif next_task == "start_leg":
                get_logger(sherpa.name).info(f"{sherpa.name} starting new leg")
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
                f"Trip information mismatch(trip_id: {req.trip_id}",
                f"trip_leg_id: {req.trip_leg_id})",
                f"ongoing_trip_id: {ongoing_trip.trip_id}",
                f"ongoing_trip_leg_id: {ongoing_trip.trip_leg_id}",
            )

        curr_station: fm.Station = self.dbsession.get_station(ongoing_trip.next_station())

        if not utils_util.are_poses_close(curr_station.pose, req.destination_pose):
            raise ValueError(
                f"{sherpa.name} sent to {curr_station.pose} but",
                f"reached {req.destination_pose}",
            )

        trip_analytics: tm.TripAnalytics = self.dbsession.get_trip_analytics(
            ongoing_trip.trip_leg_id
        )

        # end transaction
        self.dbsession.session.commit()

        # update db
        sherpa.pose = req.destination_pose
        self.end_leg(ongoing_trip, sherpa, curr_station, trip_analytics)

    def handle_induct_sherpa(self, req: rqm.SherpaInductReq):
        response = {}
        # query db
        sherpa: fm.Sherpa = self.dbsession.get_sherpa(req.sherpa_name)

        if sherpa.status.pose is None:
            raise ValueError(
                f"{sherpa.name} cannot be inducted for doing trips",
                "sherpa pose information is not available with fleet manager",
            )

        sherpa_availability = self.dbsession.get_sherpa_availability(sherpa.name)
        visa_assignments = self.dbsession.get_visa_held(sherpa.name)

        # end transaction
        self.dbsession.session.commit()

        # update db
        if not req.induct:
            for visa_assignment in visa_assignments:
                self.dbsession.session.delete(visa_assignments)

        sherpa.status.inducted = req.induct
        sherpa_availability.available = req.induct

        return response

    def handle_peripherals(self, req: rqm.SherpaPeripheralsReq):

        # query db
        sherpa: fm.Sherpa = self.dbsession.get_sherpa(req.sherpa_name)
        ongoing_trip: tm.OngoingTrip = self.dbsession.get_ongoing_trip(sherpa.name)
        curr_station: fm.Station = self.dbsession.get_station(ongoing_trip.curr_station())

        # end transaction
        self.dbsession.session.commit()

        # update db
        if not ongoing_trip:
            get_logger(sherpa.name).info(
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
            get_logger(sherpa.name).info(
                f"dispatch button not pressed on {sherpa.name}, taking no action"
            )
            return

        if tm.TripState.WAITING_STATION_DISPATCH_START not in ongoing_trip.states:
            get_logger(sherpa.name).warning(
                f"ignoring dispatch button press on {sherpa.name}"
            )
            return

        ongoing_trip.add_state(tm.TripState.WAITING_STATION_DISPATCH_END)
        get_logger(sherpa.name).info(f"dispatch button pressed on {sherpa.name}")

        # ask sherpa to stop playing the sound
        sound_msg = rqm.PeripheralsReq(
            speaker=rqm.SpeakerReq(sound=rqm.SoundEnum.wait_for_dispatch, play=False),
            indicator=rqm.IndicatorReq(pattern=rqm.PatternEnum.free, activate=True),
        )

        _: Response = utils_comms.send_msg_to_sherpa(self.dbsession, sherpa, sound_msg)

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
                get_logger(sherpa.name).error(error)
                raise ValueError(error)

            ongoing_trip.add_state(tm.TripState.WAITING_STATION_AUTO_HITCH_END)
            get_logger(sherpa.name).info(f"auto-hitch done by {sherpa.name}")

        # auto unhitch
        else:
            if tm.TripState.WAITING_STATION_AUTO_UNHITCH_START not in ongoing_trip.states:
                error = f"auto-unhitch done by {sherpa.name} without auto-unhitch command"
                get_logger(sherpa.name).error(error)
                raise ValueError(error)

            ongoing_trip.add_state(tm.TripState.WAITING_STATION_AUTO_UNHITCH_END)
            get_logger(sherpa.name).info(f"auto-unhitch done by {sherpa.name}")

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
        get_logger(sherpa.name).info(
            f"CONV_{req.direction.upper()} completed by {sherpa.name}"
        )

    def handle_conveyor_ack(
        self,
        ongoing_trip: tm.OngoingTrip,
        sherpa: fm.Sherpa,
        curr_station: fm.Station,
        req: rqm.ConveyorReq,
    ):

        fleet_name = ongoing_trip.trip.fleet_name

        conveyor_start_state = getattr(
            tm.TripState, f"WAITING_STATION_CONV_{req.direction.upper()}_START"
        )

        if conveyor_start_state not in ongoing_trip.states:
            error = (
                f"{sherpa.name} sent a invalid conveyor ack message",
                f"{ongoing_trip.states} doesn't match ack msg",
            )
            raise ValueError(error)

        if StationProperties.CONVEYOR in curr_station.properties:
            transfer_tote_msg = (
                f"will send msg to the conveyor at"
                f"station: {curr_station.name} to transfer "
                f"{req.num_units} tote(s)"
            )

            get_logger().info(transfer_tote_msg)

            if req.num_units == 2:
                msg = "transfer_2totes"
            elif req.num_units == 1:
                msg = "transfer_tote"
            utils_comms.send_msg_to_conveyor(msg, curr_station.name)

            self.dbsession.add_notification(
                [fleet_name, curr_station.name],
                transfer_tote_msg,
                mm.NotificationLevels.info,
                mm.NotificationModules.peripheral_devices,
            )

    def handle_verify_fleet_files(self, req: rqm.SherpaReq):

        # query db
        sherpa: fm.Sherpa = self.dbsession.get_sherpa(req.source)
        fleet_name = sherpa.fleet.name
        map_files = self.dbsession.get_map_files(fleet_name)

        # end transaction
        self.dbsession.session.commit()

        # update db
        ip_changed = sherpa.status.other_info.get("ip_changed", True)
        get_logger().info(f"Has sherpa ip changed: {ip_changed}")

        map_file_info = [
            rqm.MapFileInfo(file_name=mf.filename, hash=mf.file_hash) for mf in map_files
        ]

        reset_fleet = hutils.is_reset_fleet_required(fleet_name, map_files)

        if reset_fleet:
            reset_fleet_msg = (
                f"Map files of {fleet_name} has been modified",
                f"please reset the fleet {fleet_name}",
            )
            self.dbsession.add_notification(
                [fleet_name, sherpa.name],
                reset_fleet_msg,
                mm.NotificationLevels.alert,
                mm.NotificationModules.map_file_check,
            )
            get_logger().warning(reset_fleet_msg)

        map_file_info = hutils.update_map_file_info_with_certs(
            map_file_info, sherpa.name, sherpa.ip_address, ip_changed=ip_changed
        )
        response: rqm.VerifyFleetFilesResp = rqm.VerifyFleetFilesResp(
            fleet_name=fleet_name, files_info=map_file_info
        )

        self.dbsession.add_notification(
            [fleet_name, sherpa.name],
            f"{sherpa.name} connected to fleet manager!",
            mm.NotificationLevels.info,
            mm.NotificationModules.generic,
        )

        return response.to_json()

    def handle_resource_access(self, req: rqm.ResourceReq):
        sherpa: fm.Sherpa = self.dbsession.get_sherpa(req.source)
        if not req.visa:
            get_logger(sherpa.name).warning("requested access type not supported")
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

        # end transaction
        self.dbsession.session.commit()

        # update db
        if granted:
            for ezone in set(reqd_ezones):
                utils_visa.lock_exclusion_zone(ezone, sherpa)

        granted_message = "granted" if granted else "not granted"
        visa_log = (
            f"{sherpa.name} {granted_message} {req.visa_type}",
            f"type visa to zone {req.zone_name}",
        )
        get_logger().info(visa_log)
        get_logger().info(f"visa {granted_message} to {sherpa.name}")

        response: rqm.ResourceResp = rqm.ResourceResp(
            granted=granted, visa=req, access_type=rqm.AccessType.REQUEST
        )
        self.dbsession.add_notification(
            [sherpa.name],
            visa_log,
            mm.NotificationLevels.info,
            mm.NotificationModules.visa,
            repetitive=True,
            repetition_freq=15,
        )
        return response.to_json()

    def handle_visa_release(self, req: rqm.VisaReq, sherpa: fm.Sherpa):
        # query db
        visas_to_release = utils_visa.get_visas_to_release(self.dbsession, sherpa, req)

        # end transaction
        self.dbsession.session.commit()

        # update db
        for ezone in set(visas_to_release):
            utils_visa.unlock_exclusion_zone(self.dbsession, ezone, sherpa)

        visa_log = f"{sherpa.name} released {req.visa_type} visa to zone {req.zone_name}"
        get_logger().info(visa_log)
        response: rqm.ResourceResp = rqm.ResourceResp(
            granted=True, visa=req, access_type=rqm.AccessType.RELEASE
        )
        self.dbsession.add_notification(
            [sherpa.name],
            visa_log,
            mm.NotificationLevels.info,
            mm.NotificationModules.visa,
        )
        return response.to_json()

    def handle_delete_visa_assignments(self, req: rqm.DeleteVisaAssignments):

        # query db
        visa_assignments: List[vm.VisaAssignment] = self.get_all_visa_assignments()

        # end transaction
        self.dbsession.session.commit()

        # update db
        for visa_assignment in visa_assignments:
            self.dbsession.session.delete(visa_assignment)

        return {}

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

        get_logger().info(
            f"Sending request {image_update_req} to update docker image on {sherpa.name}"
        )
        utils_comms.send_msg_to_sherpa(self.dbsession, sherpa, image_update_req)
        return response

    def handle_pass_to_sherpa(self, req):
        sherpa: fm.Sherpa = self.dbsession.get_sherpa(req.sherpa_name)
        get_logger(sherpa.name).info(
            f"passing control request to sherpa {sherpa.name}, {req.dict()} "
        )
        utils_comms.send_msg_to_sherpa(self.dbsession, sherpa, req)

    def handle(self, msg):
        self.dbsession = None
        init_request_context(msg)

        with DBSession() as dbsession:
            self.dbsession = dbsession

            if msg.type == MessageType.FM_HEALTH_CHECK:
                self.run_health_check()
                return

            # log, add msg to sherpa events
            self.record_msg_received(msg, UpdateMsgs)
            handle_ok, reason = self.should_handle_msg(msg)

            if not handle_ok:
                self.ignore_msg(msg, UpdateMsgs, reason)
                return

            # get handler
            msg_handler = getattr(self, "handle_" + msg.type, None)

            if not msg_handler:
                get_logger().error(f"no handler defined for {msg.type}")
                return

            response = msg_handler(msg)

        # run optimal dispatch if needs be - need not be coupled with handler
        if msg.type in OptimalDispatchInfluencers:
            with DBSession() as dbsession:
                self.dbsession = dbsession
                self.run_optimal_dispatch()

        return response
