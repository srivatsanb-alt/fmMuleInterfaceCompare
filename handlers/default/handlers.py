from core.logs import get_logger
from endpoints.request_models import HitchMsg, InitMsg, MoveMsg, PeripheralsMsg, ReachedMsg
import handlers.default.handler_utils as hutils
from models.base_models import StationProperties
from models.db_session import DBSession
from models.fleet_models import Fleet, Sherpa, SherpaStatus, Station
from models.trip_models import OngoingTrip, PendingTrip, Trip, TripLeg
from utils.comms import send_msg_to_sherpa
from utils.util import are_poses_close

session = DBSession()


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
        if trip.finished():
            get_logger(sherpa_name).error(
                f"{sherpa_name} cannot start leg of finished trip {trip.id}"
            )
            return
        next_station: Station = session.get_station(trip.next_station())
        if are_poses_close(sherpa_status.pose, next_station.pose, sherpa_name):
            get_logger(sherpa_name).info(f"{sherpa_name} already at {next_station.name}")
            trip.end_leg()
            return
        trip_leg = hutils.start_leg(ongoing_trip, session)
        get_logger(sherpa_name).info(
            f"{sherpa_name} started leg of trip {trip.id} from {trip.curr_station()} to {trip.next_station()}"
        )
        move_msg = MoveMsg(
            trip_id=trip.id,
            trip_leg_id=trip_leg.id,
            destination_pose=next_station.pose,
            destination_name=next_station.name,
        )
        send_msg_to_sherpa(sherpa, move_msg)

    def end_leg(self, trip_leg: TripLeg):
        trip: Trip = trip_leg.trip
        sherpa_name = trip.sherpa_name
        get_logger(sherpa_name).info(
            f"{sherpa_name} finished leg of trip {trip.id} from {trip.curr_station()} to {trip.next_station()}"
        )
        hutils.end_leg(trip_leg)

    def maybe_assign_sherpa_to_pending_trip(self, sherpa_name: str):
        pending_trip: PendingTrip = session.get_pending_trip()
        if pending_trip:
            self.start_trip(pending_trip.trip, sherpa_name)
            session.delete_pending_trip(pending_trip)
            get_logger().info(f"deleted pending trip id {pending_trip.trip_id}")

    def handle_init(self, msg: InitMsg):
        sherpa_name = msg.source
        sherpa_status: SherpaStatus = session.get_sherpa_status(sherpa_name)
        sherpa_status.pose = msg.current_pose
        sherpa_status.initialized = True

        self.maybe_assign_sherpa_to_pending_trip(sherpa_name)

    def handle_reached(self, msg: ReachedMsg):
        sherpa_name = msg.source
        ongoing_trip: OngoingTrip = session.get_ongoing_trip(sherpa_name)
        trip: Trip = ongoing_trip.trip

        # TODO: Confirm that reached pose matches expected pose.
        self.end_leg(ongoing_trip.trip_leg)

        station_name = trip.curr_station()
        station: Station = session.get_station(station_name)
        # if at unhitch station send unhitch command.
        if StationProperties.AUTO_UNHITCH in station.properties:
            unhitch_msg = PeripheralsMsg(HitchMsg(False))
            send_msg_to_sherpa(sherpa_name, unhitch_msg)
            return
        # if at hitch station send hitch command.
        if StationProperties.AUTO_HITCH in station.properties:
            hitch_msg = PeripheralsMsg(HitchMsg(True))
            send_msg_to_sherpa(sherpa_name, hitch_msg)
            return

        if trip.finished():
            self.end_trip()
            self.maybe_assign_sherpa_to_pending_trip(sherpa_name)

    def handle(self, msg):
        handle_ok, reason = self.should_handle_msg(msg)
        if not handle_ok:
            get_logger().warning(f"message of type {msg.type} ignored, reason={reason}")
            return
        msg_handler = getattr(self, "handle_" + msg.type)
        msg_handler(msg)
        session.close()
