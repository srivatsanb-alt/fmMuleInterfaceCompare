from requests import Response
from core.logs import get_logger
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
from models.base_models import StationProperties
from models.db_session import session
from models.fleet_models import Fleet, Sherpa, SherpaStatus, Station
from models.trip_models import OngoingTrip, PendingTrip, Trip
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
        sherpa_name = ongoing_trip.sherpa_name
        hutils.end_trip(ongoing_trip, success, session)
        get_logger(sherpa_name).info(f"trip {ongoing_trip.trip_id} finished")

    def start_leg(self, ongoing_trip: OngoingTrip):
        trip: Trip = ongoing_trip.trip
        sherpa_name: str = trip.sherpa_name
        sherpa_status: SherpaStatus = session.get_sherpa_status(sherpa_name)
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
        if are_poses_close(sherpa_status.pose, next_station.pose, sherpa_name):
            get_logger(sherpa_name).info(f"{sherpa_name} already at {next_station.name}")
            ongoing_trip.end_leg()
            return
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

    def assign_sherpa_to_pending_trip(self, pending_trip: PendingTrip, sherpa_name: str):
        self.start_trip(pending_trip.trip, sherpa_name)
        session.delete_pending_trip(pending_trip)
        get_logger(sherpa_name).info(f"deleted pending trip id {pending_trip.trip_id}")

    def resume_ongoing_trip(self, ongoing_trip: OngoingTrip, sherpa_status: SherpaStatus):
        station_name: str = ongoing_trip.trip_leg.to_station
        station: Station = session.get_station(station_name)
        response: Response = send_move_msg(sherpa_status.sherpa, ongoing_trip, station)
        get_logger(sherpa_status.sherpa_name).info(
            f"received from {sherpa_status.sherpa_name}: status {response.status_code}"
        )

    def initialize_sherpa(self, sherpa_name):
        sherpa_status: SherpaStatus = session.get_sherpa_status(sherpa_name)
        sherpa_status.initialized = True
        sherpa_status.idle = True
        sherpa_status.disabled = False
        get_logger(sherpa_name).info(f"{sherpa_name} initialized")

        ongoing_trip: OngoingTrip = session.get_ongoing_trip(sherpa_name)
        if ongoing_trip:
            get_logger(sherpa_name).info(f"found ongoing trip id {ongoing_trip.trip_id}")
            self.resume_ongoing_trip(ongoing_trip, sherpa_status)
            return

        pending_trip: PendingTrip = session.get_pending_trip()
        if pending_trip:
            get_logger(sherpa_name).info(f"found pending trip id {pending_trip.trip_id}")
            self.assign_sherpa_to_pending_trip(pending_trip, sherpa_name)

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

        # TODO: Confirm that reached pose matches expected pose.
        self.end_leg(ongoing_trip)

        station_name = ongoing_trip.curr_station()
        station: Station = session.get_station(station_name)
        # if at unhitch station send unhitch command.
        if StationProperties.AUTO_UNHITCH in station.properties:
            get_logger(sherpa_name).info(f"{sherpa_name} reached an auto-unhitch station")
            unhitch_msg = PeripheralsReq(auto_hitch=HitchReq(hitch=False))
            response = send_msg_to_sherpa(ongoing_trip.trip.sherpa, unhitch_msg)
            get_logger(sherpa_name).info(
                f"received from {sherpa_name}: status {response.status_code}"
            )
            return
        # if at hitch station send hitch command.
        if StationProperties.AUTO_HITCH in station.properties:
            get_logger(sherpa_name).info(f"{sherpa_name} reached an auto-hitch station")
            hitch_msg = PeripheralsReq(auto_hitch=HitchReq(hitch=True))
            response = send_msg_to_sherpa(ongoing_trip.trip.sherpa, hitch_msg)
            get_logger(sherpa_name).info(
                f"received from {sherpa_name}: status {response.status_code}"
            )
            return

        if ongoing_trip.finished():
            self.end_trip(ongoing_trip)
            pending_trip: PendingTrip = session.get_pending_trip()
            if pending_trip:
                get_logger(sherpa_name).info(
                    f"found pending trip id {pending_trip.trip_id}"
                )
                self.assign_sherpa_to_pending_trip(pending_trip, sherpa_name)

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
        if req.dispatch_button:
            self.handle_dispatch_button(req.dispatch_button, sherpa_name)
        elif req.auto_hitch:
            self.handle_auto_hitch(req.auto_hitch, sherpa_name)

    def handle_auto_hitch(self, req: HitchReq, sherpa_name):
        if not req.hitch:
            # auto-unhitch done
            get_logger(sherpa_name).info(f"auto-unhitch done on {sherpa_name}")
            self.handle_next(sherpa_name)

    def handle_dispatch_button(self, req: DispatchButtonReq, sherpa_name):
        if not req.value:
            get_logger(sherpa_name).info(
                f"dispatch button not pressed on {sherpa_name}, taking no action"
            )
            return
        get_logger(sherpa_name).info(f"dispatch button pressed on {sherpa_name}")
        self.handle_next(sherpa_name)

    def handle_next(self, sherpa_name):
        ongoing_trip: OngoingTrip = session.get_ongoing_trip(sherpa_name)
        if not ongoing_trip.finished_booked():
            self.start_leg(ongoing_trip)
            return
        # booked trip done, try to assign this sherpa to a pending trip.
        pending_trip: PendingTrip = session.get_pending_trip()
        if pending_trip:
            self.end_trip(ongoing_trip)
            get_logger(sherpa_name).info(f"found pending trip id {pending_trip.trip_id}")
            self.assign_sherpa_to_pending_trip(pending_trip, sherpa_name)
        else:
            # continue with current trip (e.g. go to parking)
            self.start_leg(ongoing_trip)

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
        return response
