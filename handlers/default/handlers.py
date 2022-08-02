from core.logs import get_logger
from endpoints.request_models import InitMsg
from handlers.default.handler_utils import assign_sherpa, start_leg, start_trip
from models.db_session import DBSession
from models.fleet_models import Fleet, Sherpa, SherpaStatus, Station
from models.trip_models import OngoingTrip, PendingTrip, Trip
from utils.comms import send_move_msg
from utils.util import are_poses_close


session = DBSession()


class Handlers:
    def should_handle_msg(self, msg):
        return True, None

    def start_trip(self, trip: Trip, sherpa_name: str):
        ongoing_trip = assign_sherpa(trip, sherpa_name, session)
        start_trip(ongoing_trip, session)
        self.start_leg(ongoing_trip)

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
        get_logger(sherpa_name).info(
            f"{sherpa_name} starting leg of trip {trip.id} from {trip.curr_station()} to {trip.next_station()}"
        )
        trip_leg = start_leg(ongoing_trip, session)
        send_move_msg(
            sherpa_name, trip.id, trip_leg.id, next_station.name, next_station.pose
        )

    def handle_init(self, msg: InitMsg):
        sherpa_name = msg.source
        sherpa_status: SherpaStatus = session.get_sherpa_status(sherpa_name)
        sherpa_status.pose = msg.current_pose
        sherpa_status.initialized = True
        # If there is a pending trip, assign this sherpa to it.
        pending_trip: PendingTrip = session.get_pending_trip()
        if pending_trip:
            self.start_trip(pending_trip.trip, sherpa_name)
            session.delete_pending_trip(pending_trip)
            get_logger().info(f"deleted pending trip id {pending_trip.trip_id}")

    def handle(self, msg):
        handle_ok, reason = self.should_handle_msg(msg)
        if not handle_ok:
            get_logger().warning(f"message of type {msg.type} ignored, reason={reason}")
            return
        msg_handler = getattr(self, "handle_" + msg.type)
        msg_handler(msg)
        session.close()
