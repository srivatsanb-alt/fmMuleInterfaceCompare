from core.constants import FleetStatus, DisabledReason
from core.logs import get_logger
from models.base_models import StationProperties
from models.db_session import session
from models.fleet_models import Fleet, Sherpa, SherpaStatus, Station, SherpaEvent
from models.request_models import (
    AccessType,
    BookingReq,
    DispatchButtonReq,
    HitchReq,
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
    DeleteTripReq,
    TerminateTripReq,
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
from utils.comms import get, send_move_msg, send_msg_to_sherpa, send_status_update
from utils.util import (
    are_poses_close,
    check_if_timestamp_has_passed,
    get_table_as_dict,
    dt_to_str,
)
from utils.visa_utils import maybe_grant_visa, unlock_exclusion_zone
import redis
import os
import json
import datetime
from core.config import Config
import handlers.default.handler_utils as hutils


class RequestContext:
    msg_type: str
    sherpa_name: str
    assign_next_task: bool
    continue_curr_task: bool
    logger = None


req_ctxt = RequestContext()


def init_request_context(req):
    req_ctxt.msg_type = req.type
    if isinstance(req, SherpaReq) or isinstance(req, SherpaMsg):
        req_ctxt.sherpa_name = req.source
    else:
        req_ctxt.sherpa_name = None
    req_ctxt.assign_next_task = True
    # do not send a move to current destination, except if asked
    req_ctxt.continue_curr_task = False
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
        get_logger(sherpa_name).info(f"trip {trip.id} started")

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
            get_logger().info(
                f"stale heartbeat from sherpa {stale_sherpa_status.sherpa_name}"
            )

    def add_sherpa_events(self):
        redis_db = redis.from_url(os.getenv("FM_REDIS_URI"))
        sherpa_events = redis_db.get("sherpa_events")
        if sherpa_events:
            sherpa_events = json.loads(sherpa_events)
            for event in sherpa_events:
                self.add_sherpa_event(
                    sherpa_name=event[0], msg_type=event[1], context=event[2]
                )
        # clear sherpa events
        redis_db.delete("sherpa_events")

    def add_sherpa_event(self, sherpa_name, msg_type, context):
        sherpa_event: SherpaEvent = SherpaEvent(
            sherpa_name=sherpa_name,
            msg_type=msg_type,
            context="sent by sherpa",
        )
        session.add_to_session(sherpa_event)

    def end_leg(self, ongoing_trip: OngoingTrip):
        trip: Trip = ongoing_trip.trip

        trip.etas[ongoing_trip.next_idx_aug] = 0

        trip_analytics = session.get_trip_analytics(ongoing_trip.trip_leg_id)

        # ongoing_trip.trip_leg.end_time is set only hutils.end_leg using current time for analytics end time
        if trip_analytics:
            trip_analytics.end_time = datetime.datetime.now()
            time_delta = datetime.datetime.now() - ongoing_trip.trip_leg.start_time
            trip_analytics.actual_trip_time = time_delta.seconds

        sherpa_name = trip.sherpa_name
        get_logger(sherpa_name).info(
            f"{sherpa_name} finished leg of trip {trip.id} from {ongoing_trip.trip_leg.from_station} to {ongoing_trip.trip_leg.to_station} "
        )
        hutils.end_leg(ongoing_trip)

        self.do_post_actions(ongoing_trip)

    def recreate_milkrun(self, pending_trip: PendingTrip):

        if not check_if_timestamp_has_passed(pending_trip.trip.end_time):
            get_logger().info(
                f"recreating trip {pending_trip.trip.id}, milkrun needs to be continued"
            )
            new_metadata = pending_trip.trip.trip_metadata
            time_period = new_metadata["milkrun_time_period"]

            # modify start time
            new_start_time = datetime.datetime.now() + datetime.timedelta(
                seconds=int(time_period)
            )
            new_start_time = dt_to_str(new_start_time)
            new_metadata["milkrun_start_time"] = new_start_time

            get_logger().info(f"milkrun new metadata {new_metadata}")
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
                f"will not recreate trip {pending_trip.trip.id}, milkrun_end_time past current time"
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

        if not hutils.is_sherpa_available_for_new_trip(sherpa_status):
            get_logger(sherpa_name).info(
                f"{sherpa_name} not available for {pending_trip.trip_id}"
            )
            return False

        if pending_trip.trip.milkrun:
            self.recreate_milkrun(pending_trip)

        self.start_trip(pending_trip.trip, sherpa_name)
        session.delete_pending_trip(pending_trip)
        get_logger(sherpa_name).info(f"deleted pending trip id {pending_trip.trip_id}")

        return True

    # assigns next destination to sherpa
    def assign_next_task(self, sherpa_name):
        done = False
        ongoing_trip: OngoingTrip = session.get_ongoing_trip(sherpa_name)

        if not ongoing_trip or ongoing_trip.finished():
            self.end_trip(ongoing_trip)
            sherpa = session.get_sherpa(sherpa_name)
            sherpa.status.trip_id = None
            sherpa.status.trip_leg_id = None
            done = self.assign_new_trip(sherpa_name)

        ongoing_trip: OngoingTrip = session.get_ongoing_trip(sherpa_name)

        if (
            self.check_continue_curr_leg(ongoing_trip)
            and ongoing_trip.check_continue()
            and req_ctxt.continue_curr_task
        ):
            get_logger(sherpa_name).info(f"{sherpa_name} continuing leg")
            self.continue_leg(ongoing_trip)
            done = True
        elif (
            self.check_start_new_leg(ongoing_trip)
            and not ongoing_trip.finished_booked()
            and ongoing_trip.check_continue()
        ):
            get_logger(sherpa_name).info(f"{sherpa_name} starting new leg")
            self.start_leg(ongoing_trip)
            done = True

        if done:
            get_logger(sherpa_name).info(f"assigned next task to {sherpa_name}")
            sherpa_status = session.get_sherpa_status(sherpa_name)
            sherpa_status.idle = False
        else:
            get_logger(sherpa_name).info(f"{sherpa_name} not assigned new task")

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
        get_logger(sherpa_name).info(f"{sherpa_name} initialized")
        req_ctxt.continue_curr_task = True

    def do_pre_actions(self, ongoing_trip: OngoingTrip):
        curr_station = ongoing_trip.curr_station()
        sherpa_name = ongoing_trip.sherpa_name
        if not curr_station:
            get_logger(sherpa_name).info(
                f"no pre-actions performed since {sherpa_name} is not at a trip station"
            )
            return

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
            get_logger(sherpa_name).info(f"{sherpa_name} reached an auto-hitch station")
            hitch_msg = PeripheralsReq(auto_hitch=HitchReq(hitch=True))
            response = send_msg_to_sherpa(ongoing_trip.trip.sherpa, hitch_msg)
            get_logger(sherpa_name).info(
                f"received from {sherpa_name}: status {response.status_code}"
            )
            ongoing_trip.add_state(TripState.WAITING_STATION_AUTO_HITCH_START)

        # if at unhitch station send unhitch command.
        if StationProperties.AUTO_UNHITCH in station.properties:
            get_logger(sherpa_name).info(f"{sherpa_name} reached an auto-unhitch station")
            unhitch_msg = PeripheralsReq(auto_hitch=HitchReq(hitch=False))
            response = send_msg_to_sherpa(ongoing_trip.trip.sherpa, unhitch_msg)
            get_logger(sherpa_name).info(
                f"received from {sherpa_name}: status {response.status_code}"
            )
            ongoing_trip.add_state(TripState.WAITING_STATION_AUTO_UNHITCH_START)

        if StationProperties.DISPATCH_NOT_REQD not in station.properties:
            get_logger(sherpa_name).info(f"{sherpa_name} reached a dispatch station")
            ongoing_trip.add_state(TripState.WAITING_STATION_DISPATCH_START)
            # ask sherpa to play a sound
            sound_msg = PeripheralsReq(
                speaker=SpeakerReq(sound=SoundEnum.wait_for_dispatch, play=True),
                indicator=IndicatorReq(
                    pattern=PatternEnum.wait_for_dispatch, activate=True
                ),
            )
            response = send_msg_to_sherpa(ongoing_trip.trip.sherpa, sound_msg)

            get_logger(sherpa_name).info(
                f"sent speaker and indicator request to {sherpa_name}: response status {response.status_code}"
            )

    def delete_ongoing_trip(self, req: DeleteTripReq):
        trips = session.get_trip_with_booking_id(req.booking_id)
        for trip in trips:
            trip.status = TripStatus.CANCELLED
            ongoing_trip: OngoingTrip = session.get_ongoing_trip_with_trip_id(trip.id)
            sherpa: Sherpa = session.get_sherpa(ongoing_trip.sherpa_name)
            sherpa.status.trip_id = None
            sherpa.status.trip_leg_id = None
            terminate_trip_msg = TerminateTripReq(
                trip_id=ongoing_trip.trip_id, trip_leg_id=ongoing_trip.trip_leg_id
            )
            response = send_msg_to_sherpa(sherpa, terminate_trip_msg)
            session.delete_ongoing_trip(ongoing_trip)
        return response

    def handle_reached(self, msg: ReachedReq):
        sherpa_name = msg.source
        sherpa: SherpaStatus = session.get_sherpa_status(sherpa_name)

        ongoing_trip: OngoingTrip = session.get_ongoing_trip(sherpa_name)
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

        if msg.mode == status.mode:
            return

        status.mode = msg.mode
        get_logger(sherpa_name).info(f"{sherpa_name} switched to {msg.mode} mode")

        if msg.mode != "fleet":
            get_logger(sherpa_name).info(f"{sherpa_name} uninitialized")
            status.initialized = False
        elif not status.initialized:
            # sherpa switched to fleet mode
            init_req: InitReq = InitReq()
            response: Response = get(sherpa, init_req)
            init_resp: InitResp = InitResp.from_dict(response.json())
            get_logger(sherpa_name).info(f"received from {sherpa_name}: {init_resp}")
            self.initialize_sherpa(sherpa_name)

    def handle_induct_sherpa(self, req: SherpaInductReq):
        sherpa: Sherpa = session.get_sherpa(req.sherpa_name)
        sherpa.status.inducted = req.induct
        sherpa_availability = session.get_sherpa_availability(req.sherpa_name)
        sherpa_availability.available = req.induct

    def handle_peripherals(self, req: SherpaPeripheralsReq):
        sherpa_name = req.source
        ongoing_trip: OngoingTrip = session.get_ongoing_trip(sherpa_name)
        if not ongoing_trip:
            get_logger(sherpa_name).info(
                f"ignoring peripherals request from {sherpa_name} without ongoing trip"
            )
            return
        if req.dispatch_button:
            self.handle_dispatch_button(req.dispatch_button, ongoing_trip)
        elif req.auto_hitch:
            self.handle_auto_hitch(req.auto_hitch, ongoing_trip)

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
                trip: Trip = session.create_trip(
                    trip_msg.route,
                    trip_msg.priority,
                    trip_msg.metadata,
                    booking_id,
                    fleet_name,
                )
                session.create_pending_trip(trip.id)
        return response

    def handle_delete_ongoing_trip(self, req: DeleteTripReq):
        response = self.delete_ongoing_trip(req)
        return response

    def handle_trip_status(self, req: TripStatusMsg):
        sherpa_name = req.source
        sherpa: Sherpa = session.get_sherpa(sherpa_name)
        ongoing_trip: OngoingTrip = session.get_ongoing_trip_with_trip_id(req.trip_id)

        if not ongoing_trip:
            raise ValueError(
                f"{sherpa_name} sent a trip status but no ongoing trip data found (trip_id {req.trip_id})"
            )

        ongoing_trip.trip.etas[ongoing_trip.next_idx_aug] = req.trip_info.eta

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

    def handle_verify_fleet_files(self, req: SherpaReq):
        sherpa_name = req.source
        sherpa: Sherpa = session.get_sherpa(sherpa_name)
        fleet_name = sherpa.fleet.name
        map_files = session.get_map_files(fleet_name)
        map_file_info = [
            MapFileInfo(file_name=mf.filename, hash=mf.file_hash) for mf in map_files
        ]
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
        if visa_type == VisaType.UNPARKING:
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
        return response.to_json()

    def handle_visa_access(self, req: VisaReq, access_type: AccessType, sherpa_name):
        # do not assign next destination after processing a visa request.
        if access_type == AccessType.REQUEST:
            return self.handle_visa_request(req, sherpa_name)
        elif access_type == AccessType.RELEASE:
            return self.handle_visa_release(req, sherpa_name)

    def handle_resource_access(self, req: ResourceReq):
        sherpa_name = req.source
        if not req.visa:
            get_logger(sherpa_name).warning("requested access type not supported")
            return None
        return self.handle_visa_access(req.visa, req.access_type, sherpa_name)

    def handle(self, msg):
        init_request_context(msg)

        if req_ctxt.sherpa_name and msg.type not in ["trip_status", "sherpa_status"]:
            self.add_sherpa_event(req_ctxt.sherpa_name, msg.type, "sent by sherpa")

        if req_ctxt.sherpa_name and msg.type in ["trip_status", "sherpa_status"]:
            get_logger("status_updates").info(f"{req_ctxt.sherpa_name} :  {msg}")
        else:
            req_ctxt.logger.info(f"got message: {msg}")

        handle_ok, reason = self.should_handle_msg(msg)
        if not handle_ok:
            get_logger().warning(f"message of type {msg.type} ignored, reason={reason}")
            return

        msg_handler = getattr(self, "handle_" + msg.type, None)
        if not msg_handler:
            get_logger().error(f"no handler defined for {msg.type}")
            return

        response = msg_handler(msg)

        if req_ctxt.sherpa_name:
            self.assign_next_task(req_ctxt.sherpa_name)

        self.check_sherpa_status()

        return response
