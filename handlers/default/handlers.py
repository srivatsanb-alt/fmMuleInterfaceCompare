from core.logs import get_logger
from models.base_models import StationProperties
from models.db_session import session
from models.fleet_models import Fleet, Sherpa, SherpaStatus, Station
from models.request_models import (
    BookingReq,
    DispatchButtonReq,
    HitchReq,
    InitReq,
    InitResp,
    MapFileInfo,
    PeripheralsReq,
    ReachedReq,
    SherpaPeripheralsReq,
    SherpaReq,
    SherpaStatusMsg,
    TripStatusMsg,
    VerifyFleetFilesResp,
)
from models.trip_models import OngoingTrip, PendingTrip, Trip, TripState
from requests import Response
from utils.comms import get, send_move_msg, send_msg_to_sherpa
from utils.util import are_poses_close

import handlers.default.handler_utils as hutils


class Handlers:
    def should_handle_msg(self, msg):
        return True, None

    def start_trip(self, trip: Trip, sherpa_name: str):
        ongoing_trip = hutils.assign_sherpa(trip, sherpa_name, session)
        get_logger(sherpa_name).info(
            f"{sherpa_name} assigned trip {trip.id} with route {trip.route}"
        )
        hutils.start_trip(ongoing_trip, session)
        get_logger(sherpa_name).info(f"trip {trip.id} started")
        self.start_leg(ongoing_trip)

    def end_trip(self, ongoing_trip: OngoingTrip, success: bool = True):
        if not ongoing_trip:
            return
        sherpa_name = ongoing_trip.sherpa_name
        hutils.end_trip(ongoing_trip, success, session)
        get_logger(sherpa_name).info(f"trip {ongoing_trip.trip_id} finished")

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

    def end_leg(self, ongoing_trip: OngoingTrip):
        trip: Trip = ongoing_trip.trip
        sherpa_name = trip.sherpa_name
        get_logger(sherpa_name).info(
            f"{sherpa_name} finished leg of trip {trip.id} from {ongoing_trip.curr_station()} to {ongoing_trip.next_station()}"
        )
        hutils.end_leg(ongoing_trip)

        self.do_post_actions(ongoing_trip)

    def assign_pending_trip(self, sherpa_name: str):
        pending_trip: PendingTrip = session.get_pending_trip()
        if not pending_trip:
            get_logger(sherpa_name).info(f"no pending trip to assign to {sherpa_name}")
            return

        sherpa: SherpaStatus = session.get_sherpa_status(sherpa_name)
        if not hutils.is_sherpa_available(sherpa):
            get_logger(sherpa_name).info(f"{sherpa_name} not available for new trip")
            return

        get_logger(sherpa_name).info(f"found pending trip id {pending_trip.trip_id}")
        self.start_trip(pending_trip.trip, sherpa_name)
        session.delete_pending_trip(pending_trip)
        get_logger(sherpa_name).info(f"deleted pending trip id {pending_trip.trip_id}")

    def assign_next_task(self, sherpa_name):
        ongoing_trip: OngoingTrip = session.get_ongoing_trip(sherpa_name)

        if not ongoing_trip or ongoing_trip.finished():
            self.end_trip(ongoing_trip)
            self.assign_pending_trip(sherpa_name)
        elif not ongoing_trip.finished_booked() and ongoing_trip.check_continue():
            self.start_leg(ongoing_trip)

    def initialize_sherpa(self, sherpa_name):
        sherpa_status: SherpaStatus = session.get_sherpa_status(sherpa_name)
        sherpa_status.initialized = True
        sherpa_status.idle = True
        sherpa_status.disabled = False
        get_logger(sherpa_name).info(f"{sherpa_name} initialized")

    def do_pre_actions(self, ongoing_trip: OngoingTrip):
        curr_station = ongoing_trip.curr_station()
        sherpa_name = ongoing_trip.sherpa_name
        if not curr_station:
            get_logger(sherpa_name).info(
                f"no pre-actions performed since {sherpa_name} is not at a trip station"
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
            ongoing_trip.states.append(TripState.WAITING_STATION_AUTO_HITCH_START)

    def do_post_actions(self, ongoing_trip: OngoingTrip):
        curr_station = ongoing_trip.curr_station()
        sherpa_name = ongoing_trip.sherpa_name
        if not curr_station:
            get_logger(sherpa_name).info(
                f"no post-actions performed since {sherpa_name} is not at a trip station"
            )
            return
        station: Station = session.get_station(curr_station)
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
            sherpa.hwid = init_resp.hwid
            self.initialize_sherpa(sherpa_name)

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
        get_logger(sherpa_name).info(f"dispatch button pressed on {sherpa_name}")
        ongoing_trip.add_state(TripState.WAITING_STATION_DISPATCH_END)

    def handle_book(self, req: BookingReq):
        for trip_msg in req.trips:
            trip: Trip = session.create_trip(
                trip_msg.route, trip_msg.priority, trip_msg.metadata
            )
            sherpa: str = hutils.find_best_sherpa()
            if not sherpa:
                get_logger().info(
                    f"no sherpa available for trip {trip.id}, will assign later"
                )
                session.create_pending_trip(trip.id)
                return
            else:
                self.start_trip(trip, sherpa)

    def handle_trip_status(self, req: TripStatusMsg):
        pass

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

    def handle(self, msg):
        if isinstance(msg, SherpaReq):
            get_logger(msg.source).info(f"got message: {msg}")
        else:
            get_logger().info(f"got message: {msg}")

        handle_ok, reason = self.should_handle_msg(msg)
        if not handle_ok:
            get_logger().warning(f"message of type {msg.type} ignored, reason={reason}")
            return
        msg_handler = getattr(self, "handle_" + msg.type, None)
        if not msg_handler:
            get_logger().error(f"no handler defined for {msg.type}")
            return

        response = msg_handler(msg)

        if isinstance(msg, SherpaReq):
            self.assign_next_task(msg.source)

        return response
