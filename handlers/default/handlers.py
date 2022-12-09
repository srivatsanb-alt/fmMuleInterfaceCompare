from core.constants import FleetStatus, DisabledReason
from core.logs import get_logger
from models.base_models import StationProperties
from models.db_session import session
from models.fleet_models import Fleet, Sherpa, SherpaStatus, Station, SherpaEvent
from optimal_dispatch.dispatcher import OptimalDispatch
from models.request_models import (
    AccessType,
    BookingReq,
    DispatchButtonReq,
    HitchReq,
    ConveyorReq,
    InitReq,
    InitResp,
    MapFileInfo,
    PeripheralsReq,
    ReachedReq,
    ResourceReq,
    ResourceResp,
    SherpaMsg,
    SherpaPeripheralsReq,
    SherpaReq,
    SherpaStatusMsg,
    SherpaInductReq,
    SoundEnum,
    SpeakerReq,
    IndicatorReq,
    PatternEnum,
    TripStatusMsg,
    TripInfo,
    Stoppages,
    StoppageInfo,
    TripStatusUpdate,
    VerifyFleetFilesResp,
    VisaReq,
    VisaType,
    DeleteOngoingTripReq,
    DeleteBookedTripReq,
    TerminateTripReq,
    DeleteVisaAssignments,
    DeleteOptimalDispatchAssignments,
    SherpaImgUpdate,
    SherpaImgUpdateCtrlReq,
    AssignNextTask,
)
from models.trip_models import (
    OngoingTrip,
    PendingTrip,
    Trip,
    TripState,
    TripStatus,
    TripAnalytics,
)

from requests import Response
from utils.comms import (
    get,
    send_move_msg,
    send_msg_to_sherpa,
    send_status_update,
    send_msg_to_conveyor,
)
from utils.util import (
    are_poses_close,
    check_if_timestamp_has_passed,
    get_table_as_dict,
    dt_to_str,
)
from utils.visa_utils import maybe_grant_visa, unlock_exclusion_zone, split_zone_id
import redis
import os
import json
import datetime
from core.config import Config
import handlers.default.handler_utils as hutils


class RequestContext:
    msg_type: str
    sherpa_name: str
    logger = None


req_ctxt = RequestContext()


def init_request_context(req):
    req_ctxt.msg_type = req.type
    req_ctxt.source = req.source
    if isinstance(req, SherpaReq) or isinstance(req, SherpaMsg):
        req_ctxt.sherpa_name = req.source
        req_ctxt.source = req.source
    else:
        req_ctxt.sherpa_name = None

    # do not send a move to current destination, except if asked
    if isinstance(req, SherpaReq) or isinstance(req, SherpaMsg):
        req_ctxt.logger = get_logger(req.source)
    else:
        req_ctxt.logger = get_logger()


class Handlers:
    def should_handle_msg(self, msg):
        sherpa_name = req_ctxt.sherpa_name
        if not sherpa_name:
            return True, None
        sherpa: Sherpa = session.get_sherpa(sherpa_name)
        fleet: Fleet = sherpa.fleet
        if fleet.status == FleetStatus.PAUSED:
            return False, f"fleet {fleet.name} is paused"

        return True, None

    def start_trip(self, trip: Trip, sherpa_name: str):
        ongoing_trip = hutils.assign_sherpa(trip, sherpa_name, session)
        get_logger(sherpa_name).info(
            f"{sherpa_name} assigned trip {trip.id} with route {trip.route}"
        )
        hutils.start_trip(ongoing_trip, session)

    def end_trip(self, ongoing_trip: OngoingTrip, success: bool = True):
        if not ongoing_trip:
            return
        sherpa_name = ongoing_trip.sherpa_name
        hutils.end_trip(ongoing_trip, success, session)
        get_logger(sherpa_name).info(f"trip {ongoing_trip.trip_id} finished")

    def continue_leg(self, ongoing_trip: OngoingTrip):
        trip: Trip = ongoing_trip.trip
        sherpa_name: str = trip.sherpa_name
        sherpa: Sherpa = trip.sherpa
        sherpa.status.continue_curr_task = False

        next_station: Station = session.get_station(ongoing_trip.next_station())

        get_logger(sherpa_name).info(
            f"{sherpa_name} continuing leg of trip {trip.id} from {ongoing_trip.curr_station()} to {ongoing_trip.next_station()}"
        )
        response: Response = send_move_msg(sherpa, ongoing_trip, next_station)
        get_logger(sherpa_name).info(
            f"received from {sherpa_name}: status {response.status_code}"
        )

    def start_leg(self, ongoing_trip: OngoingTrip):
        trip: Trip = ongoing_trip.trip
        sherpa_name: str = trip.sherpa_name
        sherpa: Sherpa = trip.sherpa
        fleet: Fleet = sherpa.fleet

        if not sherpa_name:
            get_logger(fleet.name).error(f"cannot start leg of unassigned trip {trip.id}")
            return
        if ongoing_trip.finished():
            get_logger(sherpa_name).error(
                f"{sherpa_name} cannot start leg of finished trip {trip.id}"
            )
            return
        next_station: Station = session.get_station(ongoing_trip.next_station())

        ongoing_trip.clear_states()
        self.do_pre_actions(ongoing_trip)
        hutils.start_leg(ongoing_trip, session)
        get_logger(sherpa_name).info(
            f"{sherpa_name} started leg of trip {trip.id} from {ongoing_trip.curr_station()} to {ongoing_trip.next_station()}"
        )
        response: Response = send_move_msg(sherpa, ongoing_trip, next_station)
        get_logger(sherpa_name).info(
            f"received from {sherpa_name}: status {response.status_code}"
        )

    def check_sherpa_status(self):
        MULE_HEARTBEAT_INTERVAL = Config.get_fleet_comms_params()["mule_heartbeat_interval"]
        stale_sherpas_status: SherpaStatus = session.get_all_stale_sherpa_status(
            MULE_HEARTBEAT_INTERVAL
        )

        for stale_sherpa_status in stale_sherpas_status:
            if not stale_sherpa_status.disabled:
                stale_sherpa_status.disabled = True
                stale_sherpa_status.disabled_reason = DisabledReason.STALE_HEARTBEAT
            get_logger("status_updates").info(
                f"stale heartbeat from sherpa {stale_sherpa_status.sherpa_name}, last_update_at: {stale_sherpa_status.updated_at}, mule_heartbeat_interval: {MULE_HEARTBEAT_INTERVAL}"
            )

    def check_if_booking_is_valid(self, trip_msg):
        reason = None
        if trip_msg.priority <= 0.0:
            reason = f"trip priority cannot be less than/ equal to zero, priority: {trip_msg.priority}"

        for station_name in trip_msg.route:
            station = session.get_station(station_name)
            if any(
                prop in station.properties
                for prop in [StationProperties.CONVEYOR, StationProperties.CHUTE]
            ):
                trip_metadata = trip_msg.metadata
                num_units = hutils.get_conveyor_ops_info(trip_metadata)
                if not num_units:
                    reason = "No information on conveyor_ops and num units, need num units info for booking trip involving conveyor/chute stations"

                if num_units:
                    if num_units > 2 or num_units < 0:
                        reason = f"num units for conveyor transaction cannot be greater than 2 or less than 0, num_units_input: {num_units}"

        if reason:
            raise ValueError(f"{reason}")

    def add_sherpa_event(self, sherpa_name, msg_type, context):
        sherpa_event: SherpaEvent = SherpaEvent(
            sherpa_name=sherpa_name,
            msg_type=msg_type,
            context="sent by sherpa",
        )
        session.add_to_session(sherpa_event)

    def end_leg(self, ongoing_trip: OngoingTrip):
        trip: Trip = ongoing_trip.trip
        sherpa_name = trip.sherpa_name

        trip_analytics = session.get_trip_analytics(ongoing_trip.trip_leg_id)

        # ongoing_trip.trip_leg.end_time is set only hutils.end_leg using current time for analytics end time
        if trip_analytics:
            trip_analytics.end_time = datetime.datetime.now()
            time_delta = datetime.datetime.now() - ongoing_trip.trip_leg.start_time
            trip_analytics.actual_trip_time = time_delta.seconds
            get_logger(sherpa_name).info(
                f"{sherpa_name} finished leg of trip {trip.id} \n trip_analytics: {get_table_as_dict(TripAnalytics, trip_analytics)}"
            )

        get_logger(sherpa_name).info(
            f"{sherpa_name} finished leg of trip {trip.id} from {ongoing_trip.trip_leg.from_station} to {ongoing_trip.trip_leg.to_station} "
        )

        hutils.end_leg(ongoing_trip)

        self.do_post_actions(ongoing_trip)

    def should_recreate_scheduled_trip(self, pending_trip: PendingTrip):

        if not check_if_timestamp_has_passed(pending_trip.trip.end_time):
            new_metadata = pending_trip.trip.trip_metadata
            time_period = new_metadata["scheduled_time_period"]

            # modify start time
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

            new_start_time = dt_to_str(new_start_time)
            new_metadata["scheduled_start_time"] = new_start_time

            get_logger().info(f"scheduled new metadata {new_metadata}")
            new_trip: Trip = session.create_trip(
                pending_trip.trip.route,
                pending_trip.trip.priority,
                new_metadata,
                pending_trip.trip.booking_id,
                pending_trip.trip.fleet_name,
            )
            session.create_pending_trip(new_trip.id)
        else:
            get_logger().info(
                f"will not recreate trip {pending_trip.trip.id}, scheduled_end_time past current time"
            )

    def assign_new_trip(self, sherpa_name: str):

        sherpa: Sherpa = session.get_sherpa(sherpa_name)
        fleet: Fleet = sherpa.fleet

        if fleet.status == FleetStatus.STOPPED:
            get_logger(sherpa_name).info(
                f"fleet {fleet.name} is stopped, not assigning new trip to {sherpa_name}"
            )
            return False

        pending_trip: PendingTrip = session.get_pending_trip(sherpa_name)

        if not pending_trip:
            # get_logger(sherpa_name).info(f"no pending trip to assign to {sherpa_name}")
            return False

        get_logger(sherpa_name).info(
            f"found pending trip id {pending_trip.trip_id}, route: {pending_trip.trip.route}"
        )

        sherpa_status: SherpaStatus = session.get_sherpa_status(sherpa_name)
        sherpa_status.continue_curr_task = False

        if not hutils.is_sherpa_available_for_new_trip(sherpa_status):
            get_logger(sherpa_name).info(
                f"{sherpa_name} not available for {pending_trip.trip_id}"
            )
            return False

        if pending_trip.trip.scheduled:
            self.should_recreate_scheduled_trip(pending_trip)

        self.start_trip(pending_trip.trip, sherpa_name)
        session.delete_pending_trip(pending_trip)
        get_logger(sherpa_name).info(f"deleted pending trip id {pending_trip.trip_id}")

        return True

    # run optimal_dispatch
    def run_optimal_dispatch(self):

        optimal_dispatch_config = Config.get_optimal_dispatch_config()
        optimal_dispatch = OptimalDispatch(optimal_dispatch_config)
        optimal_dispatch.run(session)

    def check_continue_curr_leg(self, ongoing_trip: OngoingTrip):
        return (
            ongoing_trip and ongoing_trip.trip_leg and not ongoing_trip.trip_leg.finished()
        )

    def check_start_new_leg(self, ongoing_trip: OngoingTrip):
        if not ongoing_trip:
            return False
        if not ongoing_trip.trip_leg:
            return True
        if ongoing_trip.trip_leg.finished():
            return True

    def initialize_sherpa(self, sherpa_name):
        sherpa_status: SherpaStatus = session.get_sherpa_status(sherpa_name)
        sherpa_status.initialized = True
        sherpa_status.idle = True
        sherpa_status.continue_curr_task = True
        get_logger(sherpa_name).info(f"{sherpa_name} initialized")

    def do_pre_actions(self, ongoing_trip: OngoingTrip):
        curr_station = ongoing_trip.curr_station()
        sherpa_name = ongoing_trip.sherpa_name
        if not curr_station:
            get_logger(sherpa_name).info(
                f"no pre-actions performed since {sherpa_name} is not at a trip station"
            )
            return

    def add_dispatch_start_to_ongoing_trip(self, ongoing_trip):
        ongoing_trip.add_state(TripState.WAITING_STATION_DISPATCH_START)
        sound_msg = PeripheralsReq(
            speaker=SpeakerReq(sound=SoundEnum.wait_for_dispatch, play=True),
            indicator=IndicatorReq(pattern=PatternEnum.wait_for_dispatch, activate=True),
        )
        response = send_msg_to_sherpa(ongoing_trip.trip.sherpa, sound_msg)
        get_logger(ongoing_trip.sherpa_name).info(
            f"sent speaker and indicator request to {ongoing_trip.sherpa_name}: response status {response.status_code}"
        )

    def add_auto_hitch_start_to_ongoing_trip(self, ongoing_trip):
        hitch_msg = PeripheralsReq(auto_hitch=HitchReq(hitch=True))
        response = send_msg_to_sherpa(ongoing_trip.trip.sherpa, hitch_msg)
        get_logger(ongoing_trip.sherpa_name).info(
            f"received from {ongoing_trip.sherpa_name}: status {response.status_code}"
        )
        ongoing_trip.add_state(TripState.WAITING_STATION_AUTO_HITCH_START)

    def add_auto_unhitch_start_to_ongoing_trip(self, ongoing_trip):
        unhitch_msg = PeripheralsReq(auto_hitch=HitchReq(hitch=False))
        response = send_msg_to_sherpa(ongoing_trip.trip.sherpa, unhitch_msg)
        get_logger(ongoing_trip.sherpa_name).info(
            f"received from {ongoing_trip.sherpa_name}: status {response.status_code}"
        )
        ongoing_trip.add_state(TripState.WAITING_STATION_AUTO_UNHITCH_START)

    def add_conveyor_start_to_ongoing_trip(self, ongoing_trip, station):
        trip_metadata = ongoing_trip.trip.trip_metadata
        num_units = hutils.get_conveyor_ops_info(trip_metadata)

        if num_units == 0:
            get_logger().info(
                f"will not send conveyor msg to {ongoing_trip.sherpa_name}, reason: num_units is {num_units}"
            )
            return

        direction = "send" if StationProperties.CHUTE in station.properties else "receive"
        station_type = (
            "chute" if StationProperties.CHUTE in station.properties else "conveyor"
        )
        if not num_units:
            raise ValueError(
                f"{ongoing_trip.sherpa_name} has reached a {station_type} station, no tote info available in trip metadata"
            )
        conveyor_send_msg = PeripheralsReq(
            conveyor=ConveyorReq(direction=direction, num_units=num_units)
        )
        response = send_msg_to_sherpa(ongoing_trip.trip.sherpa, conveyor_send_msg)
        get_logger(ongoing_trip.sherpa_name).info(
            f"received from {ongoing_trip.sherpa_name}: status {response.status_code}"
        )
        conveyor_start_state = getattr(
            TripState, f"WAITING_STATION_CONV_{direction.upper()}_START"
        )
        ongoing_trip.add_state(conveyor_start_state)

    def do_post_actions(self, ongoing_trip: OngoingTrip):
        curr_station = ongoing_trip.curr_station()
        sherpa_name = ongoing_trip.sherpa_name

        if not curr_station:
            get_logger(sherpa_name).info(
                f"no post-actions performed since {sherpa_name} is not at a trip station"
            )
            return
        station: Station = session.get_station(curr_station)

        # if at hitch station send hitch command.
        if StationProperties.AUTO_HITCH in station.properties:
            get_logger(sherpa_name).info(f"{sherpa_name} reached a auto hitch station")
            self.add_auto_hitch_start_to_ongoing_trip(ongoing_trip)

        # if at unhitch station send unhitch command.
        if StationProperties.AUTO_UNHITCH in station.properties:
            get_logger(sherpa_name).info(f"{sherpa_name} reached an auto-unhitch station")
            self.add_auto_unhitch_start_to_ongoing_trip(ongoing_trip)

        if StationProperties.DISPATCH_NOT_REQD not in station.properties:
            get_logger(sherpa_name).info(f"{sherpa_name} reached a dispatch station")
            self.add_dispatch_start_to_ongoing_trip(ongoing_trip)

        if any(
            prop in station.properties
            for prop in [StationProperties.CONVEYOR, StationProperties.CHUTE]
        ):
            get_logger(sherpa_name).info(f"{sherpa_name} reached a dispatch station")
            self.add_conveyor_start_to_ongoing_trip(ongoing_trip, station)

    def resolve_auto_hitch_error(self, req: SherpaPeripheralsReq):
        sherpa_name = req.source
        ongoing_trip: OngoingTrip = session.get_ongoing_trip(sherpa_name)

        if not ongoing_trip:
            raise ValueError(
                f"Cannot resolve {req.error_device} error for {sherpa_name}, reason: no ongoing_trip"
            )

        peripheral_info = req.auto_hitch
        if not peripheral_info.hitch:
            if TripState.WAITING_STATION_AUTO_UNHITCH_START in ongoing_trip.states:
                ongoing_trip.add_state(TripState.WAITING_STATION_AUTO_UNHITCH_END)
                get_logger().info(
                    f"Resolving {req.error_device} error for {sherpa_name}, will wait for dispatch button to continue"
                )
                self.add_dispatch_start_to_ongoing_trip(ongoing_trip)

            else:
                get_logger().info(
                    f"Ignoring {req.error_device} error message from {sherpa_name}"
                )

        if peripheral_info.hitch:
            get_logger().info(
                f"Cannot resolve {req.error_device} error for {sherpa_name}, {req}"
            )

    def resolve_conveyor_error(self, req: SherpaPeripheralsReq):
        sherpa_name = req.source
        ongoing_trip: OngoingTrip = session.get_ongoing_trip(sherpa_name)

        if not ongoing_trip:
            raise ValueError(
                f"Cannot resolve {req.error_device} error for {sherpa_name}, reason: no ongoing_trip"
            )

        direction = req.conveyor.direction
        conveyor_start_state = getattr(
            TripState, f"WAITING_STATION_CONV_{direction.upper()}_START"
        )
        conveyor_end_state = getattr(
            TripState, f"WAITING_STATION_CONV_{direction.upper()}_END"
        )
        if conveyor_start_state in ongoing_trip.states:
            ongoing_trip.add_state(conveyor_end_state)
            get_logger().info(
                f"Resolving {req.error_device} error for {sherpa_name}, will wait for dispatch button to continue"
            )
            self.add_dispatch_start_to_ongoing_trip(ongoing_trip)
        else:
            get_logger().info(
                f"Ignoring {req.error_device} error message from {sherpa_name}"
            )

    def delete_ongoing_trip(self, req: DeleteOngoingTripReq):
        trips = session.get_trip_with_booking_id(req.booking_id)
        for trip in trips:
            ongoing_trip: OngoingTrip = session.get_ongoing_trip_with_trip_id(trip.id)
            if ongoing_trip:
                get_logger().info(
                    f"Deleting ongoing trip  - trip_id: {trip.id}, booking_id: {req.booking_id}"
                )
                sherpa: Sherpa = session.get_sherpa(ongoing_trip.sherpa_name)
                self.end_trip(ongoing_trip, False)
                trip.cancel()
                terminate_trip_msg = TerminateTripReq(
                    trip_id=ongoing_trip.trip_id, trip_leg_id=ongoing_trip.trip_leg_id
                )
                _ = send_msg_to_sherpa(sherpa, terminate_trip_msg)
                get_logger().info(
                    f"Deleted ongoing trip successfully - trip_id: {trip.id}, booking_id: {req.booking_id}"
                )
            else:
                get_logger().info(
                    f"No ongoing trip  - trip_id: {trip.id}, booking_id: {req.booking_id}"
                )

        return {}

    def should_assign_next_task(self, sherpa_name):
        done = False
        next_task = "no new task to assign"
        ongoing_trip: OngoingTrip = session.get_ongoing_trip(sherpa_name)
        sherpa_status: SherpaStatus = session.get_sherpa_status(sherpa_name)

        if not ongoing_trip:
            pending_trip: PendingTrip = session.get_pending_trip(sherpa_name)
            if pending_trip:
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
            get_logger("status_updates").info(f"{sherpa_name} not assigned new task")

        sherpa_status = session.get_sherpa_status(sherpa_name)

        if done:
            sherpa_status.assign_next_task = True
        else:
            sherpa_status.assign_next_task = False

        return done, next_task

    # assigns next destination to sherpa
    def handle_assign_next_task(self, req: AssignNextTask):
        done, next_task = self.should_assign_next_task(req.sherpa_name)
        sherpa_status: SherpaStatus = session.get_sherpa_status(req.sherpa_name)
        sherpa_status.assign_next_task = False

        valid_tasks = ["assign_new_trip", "end_ongoing_trip", "continue_leg", "start_leg"]

        if done and next_task in valid_tasks:
            ongoing_trip: OngoingTrip = session.get_ongoing_trip(req.sherpa_name)
            if next_task == "assign_new_trip":
                get_logger("status_updates").info(
                    f"will try to assign a new trip for {req.sherpa_name}, ongoing completed"
                )
                self.assign_new_trip(req.sherpa_name)
                return

            if not ongoing_trip:
                raise ValueError(
                    f"No ongoing trip, {req.sherpa_name}, next_task: {done, next_task}"
                )

            if next_task == "end_ongoing_trip":
                self.end_trip(ongoing_trip)

            if next_task == "continue_leg":
                get_logger(req.sherpa_name).info(f"{req.sherpa_name} continuing leg")
                self.continue_leg(ongoing_trip)

            elif next_task == "start_leg":
                get_logger(req.sherpa_name).info(f"{req.sherpa_name} starting new leg")
                self.start_leg(ongoing_trip)

    def handle_reached(self, msg: ReachedReq):
        sherpa_name = msg.source
        sherpa: SherpaStatus = session.get_sherpa_status(sherpa_name)

        ongoing_trip: OngoingTrip = session.get_ongoing_trip(sherpa_name)

        if (
            ongoing_trip.trip_leg_id != msg.trip_leg_id
            or ongoing_trip.trip_id != msg.trip_id
        ):
            raise ValueError(
                f"Trip information mismatch(trip_id: {msg.trip_id}, trip_leg_id: {msg.trip_leg_id}), ongoing_trip_id: {ongoing_trip.trip_id}, ongoing_trip_leg_id: {ongoing_trip.trip_leg_id}"
            )

        dest_pose = session.get_station(ongoing_trip.next_station()).pose
        if not are_poses_close(dest_pose, msg.destination_pose):
            raise ValueError(
                f"{sherpa_name} sent to {dest_pose} but reached {msg.destination_pose}"
            )
        sherpa.pose = msg.destination_pose
        self.end_leg(ongoing_trip)

    def handle_sherpa_status(self, msg: SherpaStatusMsg):
        sherpa_name = msg.sherpa_name
        sherpa: Sherpa = session.get_sherpa(sherpa_name)
        status: SherpaStatus = session.get_sherpa_status(sherpa_name)

        status.pose = msg.current_pose
        status.battery_status = msg.battery_status
        status.error = msg.error_info if msg.error else None

        if status.disabled and status.disabled_reason == DisabledReason.STALE_HEARTBEAT:
            status.disabled = False
            status.disabled_reason = None

        if msg.mode != "fleet":
            get_logger(sherpa_name).info(f"{sherpa_name} uninitialized")
            status.initialized = False
            status.continue_curr_task = False

        elif not status.initialized:
            # sherpa switched to fleet mode
            init_req: InitReq = InitReq()
            response: Response = get(sherpa, init_req)
            init_resp: InitResp = InitResp.from_dict(response.json())
            get_logger(sherpa_name).info(f"received from {sherpa_name}: {init_resp}")
            self.initialize_sherpa(sherpa_name)

        if msg.mode == status.mode:
            return

        status.mode = msg.mode
        get_logger(sherpa_name).info(f"{sherpa_name} switched to {msg.mode} mode")

    def handle_induct_sherpa(self, req: SherpaInductReq):
        response = {}
        sherpa: Sherpa = session.get_sherpa(req.sherpa_name)

        if sherpa.status.pose is None:
            raise ValueError(
                f"{req.sherpa_name} cannot be inducted for doing trips, sherpa pose information is not available with fleet manager"
            )

        sherpa.status.inducted = req.induct
        sherpa_availability = session.get_sherpa_availability(req.sherpa_name)
        sherpa_availability.available = req.induct

        if not req.induct:
            session.clear_visa_held_by_sherpa(req.sherpa_name)
        return response

    def handle_sherpa_img_update(self, req: SherpaImgUpdateCtrlReq):
        sherpa_name = req.sherpa_name
        sherpa = session.get_sherpa(sherpa_name)
        fleet_config = Config.read_config()
        # ip_address = os.getenv("FM_SERVER_IP")
        image_tag = os.getenv("MULE_IMAGE_ID")
        fm_host_name = os.getenv("HOSTNAME")
        time_zone = os.getenv("PGTZ")

        # temp sol - needs modification - all_server_ips
        ip_address = fleet_config["fleet"]["all_server_ips"][0]
        registry_port = fleet_config["docker_registry"]["port"]
        image_update_req: SherpaImgUpdate = SherpaImgUpdate(
            ip_address=ip_address,
            image_tag=image_tag,
            registry_port=registry_port,
            fm_host_name=fm_host_name,
            time_zone=time_zone,
        )
        get_logger().info(
            f"Sending request {image_update_req} to update docker image on {sherpa_name}"
        )
        send_msg_to_sherpa(sherpa, image_update_req)
        return

    def handle_peripheral_error(self, req: SherpaPeripheralsReq):

        valid_error_devices = ["auto_hitch", "conveyor"]
        if req.error_device in valid_error_devices:
            # get error resolver
            peripheral_error_resolver = getattr(
                self, f"resolve_{req.error_device}_error", None
            )
            peripheral_info = getattr(req, req.error_device, None)
            if peripheral_info is not None and peripheral_error_resolver is not None:
                peripheral_error_resolver(req)
            else:
                raise ValueError(f"Unable to resolve {req.error_device} peripheral error")
        else:
            raise ValueError(f" {req.error_device} peripheral error can't be handled")

    def handle_peripherals(self, req: SherpaPeripheralsReq):
        sherpa_name = req.source
        ongoing_trip: OngoingTrip = session.get_ongoing_trip(sherpa_name)
        if not ongoing_trip:
            get_logger(sherpa_name).info(
                f"ignoring peripherals request from {sherpa_name} without ongoing trip"
            )
            return

        if req.error_device:
            self.handle_peripheral_error(req)
            return

        if req.dispatch_button:
            self.handle_dispatch_button(req.dispatch_button, ongoing_trip)
        elif req.auto_hitch:
            self.handle_auto_hitch(req.auto_hitch, ongoing_trip)
        elif req.conveyor:
            conveyor_ack = req.conveyor.ack
            if conveyor_ack:
                self.handle_conveyor_ack(req.conveyor, ongoing_trip)
                return
            self.handle_conveyor(req.conveyor, ongoing_trip)

    def handle_conveyor_ack(self, req: ConveyorReq, ongoing_trip: OngoingTrip):
        current_station = ongoing_trip.curr_station()

        conveyor_start_state = getattr(
            TripState, f"WAITING_STATION_CONV_{req.direction.upper()}_START"
        )

        if conveyor_start_state not in ongoing_trip.states:
            error = f"{ongoing_trip.sherpa_name} sent a invalid conveyor ack message, {ongoing_trip.states} doesn't match ack msg"
            raise ValueError(error)

        get_logger().info(
            f"will send conveyor msg(direction: {req.direction}, num_units: {req.num_units}) to {current_station}"
        )

        if req.num_units == 2:
            msg = "transfer_2totes"
        elif req.num_units == 1:
            msg = "transfer_tote"

        send_msg_to_conveyor(msg, current_station)

    def handle_conveyor(self, req: ConveyorReq, ongoing_trip: OngoingTrip):
        sherpa_name = ongoing_trip.sherpa_name
        conveyor_start_state = getattr(
            TripState, f"WAITING_STATION_CONV_{req.direction.upper()}_START"
        )

        if conveyor_start_state not in ongoing_trip.states:
            error = f"{ongoing_trip.sherpa_name} {req.direction} totes without conveyor {req.direction} command"
            raise ValueError(error)

        conveyor_end_state = getattr(
            TripState, f"WAITING_STATION_CONV_{req.direction.upper()}_END"
        )
        get_logger(sherpa_name).info(f"CONV_{req.direction.upper()} done by {sherpa_name}")
        ongoing_trip.add_state(conveyor_end_state)

    def handle_auto_hitch(self, req: HitchReq, ongoing_trip: OngoingTrip):
        sherpa_name = ongoing_trip.sherpa_name
        if req.hitch:
            # auto hitch
            if TripState.WAITING_STATION_AUTO_HITCH_START not in ongoing_trip.states:
                error = f"auto-hitch done by {sherpa_name} without auto-hitch command"
                get_logger(sherpa_name).error(error)
                raise ValueError(error)
            get_logger(sherpa_name).info(f"auto-hitch done by {sherpa_name}")
            ongoing_trip.add_state(TripState.WAITING_STATION_AUTO_HITCH_END)
        else:
            # auto unhitch
            if TripState.WAITING_STATION_AUTO_UNHITCH_START not in ongoing_trip.states:
                error = f"auto-unhitch done by {sherpa_name} without auto-unhitch command"
                get_logger(sherpa_name).error(error)
                raise ValueError(error)
            get_logger(sherpa_name).info(f"auto-unhitch done by {sherpa_name}")
            ongoing_trip.add_state(TripState.WAITING_STATION_AUTO_UNHITCH_END)

    def handle_dispatch_button(self, req: DispatchButtonReq, ongoing_trip: OngoingTrip):
        sherpa_name = ongoing_trip.sherpa_name
        if not req.value:
            get_logger(sherpa_name).info(
                f"dispatch button not pressed on {sherpa_name}, taking no action"
            )
            return
        if TripState.WAITING_STATION_DISPATCH_START not in ongoing_trip.states:
            get_logger(sherpa_name).error(
                f"ignoring dispatch button press on {sherpa_name}"
            )
            return
        get_logger(sherpa_name).info(f"dispatch button pressed on {sherpa_name}")
        ongoing_trip.add_state(TripState.WAITING_STATION_DISPATCH_END)
        # ask sherpa to stop playing the sound
        sound_msg = PeripheralsReq(
            speaker=SpeakerReq(sound=SoundEnum.wait_for_dispatch, play=False),
            indicator=IndicatorReq(pattern=PatternEnum.free, activate=True),
        )
        response = send_msg_to_sherpa(ongoing_trip.trip.sherpa, sound_msg)
        get_logger(sherpa_name).info(
            f"sent speaker request to {sherpa_name}: response status {response.status_code}"
        )

    def handle_book(self, req: BookingReq):
        response = {}
        for trip_msg in req.trips:
            booking_id = session.get_new_booking_id()
            fleet_name = session.get_fleet_name_from_route(trip_msg.route)
            if fleet_name:
                # need priority for optimal dispatch logic, default is 1
                if not trip_msg.priority:
                    trip_msg.priority = 1.0

                self.check_if_booking_is_valid(trip_msg)

                trip: Trip = session.create_trip(
                    trip_msg.route,
                    trip_msg.priority,
                    trip_msg.metadata,
                    booking_id,
                    fleet_name,
                )
                session.create_pending_trip(trip.id)
                response.update(
                    {trip.id: {"booking_id": trip.booking_id, "status": trip.status}}
                )
                get_logger().info(
                    f"Created a pending trip : trip_id: {trip.id}, booking_id: {trip.booking_id}"
                )
        return response

    def handle_delete_ongoing_trip(self, req: DeleteOngoingTripReq):
        response = self.delete_ongoing_trip(req)
        return response

    def handle_delete_booked_trip(self, req: DeleteBookedTripReq):
        trips = session.get_trip_with_booking_id(req.booking_id)
        valid_trip_status = [TripStatus.BOOKED, TripStatus.ASSIGNED]
        for trip in trips:
            if trip.status in valid_trip_status:
                pending_trip: PendingTrip = session.get_pending_trip_with_trip_id(trip.id)
                session.delete_pending_trip(pending_trip)
                trip.status = TripStatus.CANCELLED
                get_logger().info(
                    f"Successfully deleted booked trip trip_id: {trip.id}, booking_id: {trip.booking_id}"
                )

    def handle_trip_status(self, req: TripStatusMsg):
        sherpa_name = req.source
        sherpa: Sherpa = session.get_sherpa(sherpa_name)
        ongoing_trip: OngoingTrip = session.get_ongoing_trip_with_trip_id(req.trip_id)

        if not ongoing_trip:
            get_logger().info(
                f"Trip status sent by {sherpa_name} is invalid/delayed, no ongoing trip data found trip_id: {req.trip_id}"
            )
            return

        if req.trip_leg_id != ongoing_trip.trip_leg_id:
            get_logger().info(
                f"Trip status sent by {sherpa_name} is invalid, sherpa_trip_leg_id: {req.trip_leg_id}, FM_trip_leg_id: {ongoing_trip.trip_leg_id}"
            )
            return

        if not ongoing_trip.next_station():
            get_logger().info(
                f"Trip status sent by {sherpa_name} is delayed, all trip legs completed trip_id: {req.trip_id}"
            )
            return

        ongoing_trip.trip.update_etas(float(req.trip_info.eta), ongoing_trip.next_idx_aug)

        trip_analytics = session.get_trip_analytics(ongoing_trip.trip_leg_id)

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
            trip_analytics: TripAnalytics = TripAnalytics(
                sherpa_name=sherpa_name,
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
            session.add_to_session(trip_analytics)
            get_logger().info(
                f"added TripAnalytics entry for trip_leg_id: {ongoing_trip.trip_leg_id}"
            )

        trip_status_update = {}

        # send to frontend
        trip_status_update.update(
            {
                "type": "trip_status",
                "sherpa_name": sherpa_name,
                "fleet_name": sherpa.fleet.name,
            }
        )

        trip_status_update.update(get_table_as_dict(TripAnalytics, trip_analytics))
        trip_status_update.update({"stoppages": {"type": req.stoppages.type}})
        send_status_update(trip_status_update)

    def handle_delete_optimal_dispatch_assignments(
        self, req: DeleteOptimalDispatchAssignments
    ):
        ptrips = session.get_pending_trips_with_fleet_name(req.fleet_name)
        for ptrip in ptrips:
            ptrip.trip.sherpa_name = None
            ptrip.trip.status = TripStatus.BOOKED
            ptrip.sherpa_name = None

        return {}

    def handle_verify_fleet_files(self, req: SherpaReq):
        sherpa_name = req.source
        sherpa: Sherpa = session.get_sherpa(sherpa_name)
        fleet_name = sherpa.fleet.name
        map_files = session.get_map_files(fleet_name)

        ip_changed = sherpa.status.other_info.get("ip_changed", True)
        get_logger().info(f"Has sherpa ip changed: {ip_changed}")

        map_file_info = [
            MapFileInfo(file_name=mf.filename, hash=mf.file_hash) for mf in map_files
        ]

        map_file_info = hutils.update_map_file_info_with_certs(
            map_file_info, sherpa.name, sherpa.ip_address, ip_changed=ip_changed
        )
        response: VerifyFleetFilesResp = VerifyFleetFilesResp(
            fleet_name=fleet_name, files_info=map_file_info
        )
        return response.to_json()

    def handle_pass_to_sherpa(self, req):
        sherpa: Sherpa = session.get_sherpa(req.sherpa_name)
        get_logger(sherpa.name).info(
            f"passing control request to sherpa {sherpa.name}, {req.dict()} "
        )
        send_msg_to_sherpa(sherpa, req)

    def handle_visa_release(self, req: VisaReq, sherpa_name):
        visa_type = req.visa_type
        zone_name = req.zone_name
        if visa_type in [VisaType.UNPARKING, VisaType.SEZ]:
            unlock_exclusion_zone(zone_name, "station", sherpa_name)
            unlock_exclusion_zone(zone_name, "lane", sherpa_name)
        elif visa_type == VisaType.TRANSIT:
            unlock_exclusion_zone(zone_name, "lane", sherpa_name)

        get_logger(sherpa_name).info(
            f"{sherpa_name} released {visa_type} visa to zone {zone_name}"
        )
        response: ResourceResp = ResourceResp(
            granted=True, visa=req, access_type=AccessType.RELEASE
        )
        get_logger().info(f"visa released by {sherpa_name}")

        return response.to_json()

    def handle_visa_request(self, req: VisaReq, sherpa_name):
        visa_type = req.visa_type
        zone_name = req.zone_name
        granted = maybe_grant_visa(zone_name, visa_type, sherpa_name)
        granted_message = "granted" if granted else "not granted"
        get_logger(sherpa_name).info(
            f"{sherpa_name} requested {visa_type} visa to zone {zone_name}: {granted_message}"
        )
        response: ResourceResp = ResourceResp(
            granted=granted, visa=req, access_type=AccessType.REQUEST
        )
        get_logger().info(f"visa {granted_message} to {sherpa_name}")
        return response.to_json()

    def handle_visa_access(self, req: VisaReq, access_type: AccessType, sherpa_name):
        # do not assign next destination after processing a visa request.
        if access_type == AccessType.REQUEST:
            return self.handle_visa_request(req, sherpa_name)
        elif access_type == AccessType.RELEASE:
            return self.handle_visa_release(req, sherpa_name)

    def handle_delete_visa_assignments(self, req: DeleteVisaAssignments):
        session.clear_all_visa_assignments()
        return {}

    def handle_resource_access(self, req: ResourceReq):
        sherpa_name = req.source
        if not req.visa:
            get_logger(sherpa_name).warning("requested access type not supported")
            return None
        return self.handle_visa_access(req.visa, req.access_type, sherpa_name)

    def handle(self, msg):
        init_request_context(msg)
        update_msgs = ["trip_status", "sherpa_status"]

        if req_ctxt.sherpa_name and msg.type not in update_msgs:
            self.add_sherpa_event(req_ctxt.sherpa_name, msg.type, "sent by sherpa")

        if msg.type in update_msgs:
            get_logger("status_updates").info(f"{req_ctxt.sherpa_name} :  {msg}")
        else:
            get_logger().info(
                f"Got message of type {msg.type} from {req_ctxt.source} \n Message: {msg} \n"
            )

        handle_ok, reason = self.should_handle_msg(msg)
        if not handle_ok:
            if msg.type in update_msgs:
                get_logger("status_updates").warning(
                    f"message of type {msg.type} ignored, reason={reason}"
                )
            else:
                get_logger().warning(f"message of type {msg.type} ignored, reason={reason}")
            return

        msg_handler = getattr(self, "handle_" + msg.type, None)
        if not msg_handler:
            get_logger().error(f"no handler defined for {msg.type}")
            return

        assign_next_task_reason = None
        if msg.type == "assign_next_task":
            if msg.sherpa_name is None:
                self.run_optimal_dispatch()
                return

            _, assign_next_task_reason = self.should_assign_next_task(msg.sherpa_name)

        response = msg_handler(msg)

        if req_ctxt.sherpa_name:
            done, next_task = self.should_assign_next_task(req_ctxt.sherpa_name)

        self.check_sherpa_status()

        # status updates, visa request - wouldn't modify optimal dispatch assignment
        optimal_dispatch_influencers = [
            "book",
            "delete_ongoing_trip",
            "delete_booked_trip",
            "induct_sherpa",
            "pass_to_sherpa",
        ]

        if msg.type in optimal_dispatch_influencers:
            self.run_optimal_dispatch()

        return response
