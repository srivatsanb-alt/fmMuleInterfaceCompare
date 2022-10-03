from typing import Dict, List
from core.logs import get_logger
from models.db_session import DBSession, session
from models.fleet_models import SherpaStatus
from models.trip_models import OngoingTrip, Trip, TripLeg


AVAILABLE = "available"


def assign_sherpa(trip: Trip, sherpa: str, session: DBSession):
    ongoing_trip = session.create_ongoing_trip(sherpa, trip.id)
    trip.assign_sherpa(sherpa)
    sherpa_status = session.get_sherpa_status(sherpa)
    sherpa_status.idle = False
    sherpa_status.trip_id = trip.id
    get_logger(sherpa).info(f"assigned trip id {trip.id} to {sherpa}")
    return ongoing_trip


def start_trip(ongoing_trip: OngoingTrip, session: DBSession):
    ongoing_trip.trip.start()


def end_trip(ongoing_trip: OngoingTrip, success: bool, session: DBSession):
    ongoing_trip.trip.end(success)
    session.delete_ongoing_trip(ongoing_trip)
    sherpa_status = session.get_sherpa_status(ongoing_trip.sherpa_name)
    sherpa_status.idle = True


def start_leg(ongoing_trip: OngoingTrip, session: DBSession) -> TripLeg:
    trip: Trip = ongoing_trip.trip
    trip_leg: TripLeg = session.create_trip_leg(
        trip.id, ongoing_trip.curr_station(), ongoing_trip.next_station()
    )
    ongoing_trip.start_leg(trip_leg.id)
    sherpa_name = ongoing_trip.sherpa_name
    if ongoing_trip.curr_station():
        update_leg_curr_station(ongoing_trip.curr_station(), sherpa_name, session)
    update_leg_next_station(ongoing_trip.next_station(), sherpa_name, session)

    return trip_leg


def end_leg(ongoing_trip: OngoingTrip):
    ongoing_trip.trip_leg.end()
    ongoing_trip.end_leg()


def update_leg_curr_station(curr_station_name: str, sherpa: str, session: DBSession):
    curr_station_status = session.get_station_status(curr_station_name)
    if not curr_station_status:
        return
    if sherpa in curr_station_status.arriving_sherpas:
        curr_station_status.arriving_sherpas.remove(sherpa)


def update_leg_next_station(next_station_name: str, sherpa: str, session: DBSession):
    next_station_status = session.get_station_status(next_station_name)
    if not next_station_status:
        return
    next_station_status.arriving_sherpas.append(sherpa)


def is_sherpa_available(sherpa):
    reason = None
    if not reason and not sherpa.inducted:
        reason = "out of fleet"
    if not reason and not sherpa.idle:
        reason = "not idle"
    if not reason:
        reason = AVAILABLE
    return reason == AVAILABLE, reason


def get_sherpa_availability(all_sherpas: List[SherpaStatus]):
    availability = {}

    for sherpa in all_sherpas:
        available, reason = is_sherpa_available(sherpa)
        availability[sherpa.sherpa_name] = available, reason

    return availability


def find_best_sherpa():
    all_sherpas: List[SherpaStatus] = session.get_all_sherpa_status()
    availability: Dict[str, str] = get_sherpa_availability(all_sherpas)
    get_logger().info(f"sherpa availability: {availability}")

    for name, (available, _) in availability.items():
        if available:
            get_logger().info(f"found {name}")
            return name

    return None
