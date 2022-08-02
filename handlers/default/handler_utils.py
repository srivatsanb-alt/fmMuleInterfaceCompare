from core.logs import get_logger
from models.db_session import DBSession
from models.trip_models import OngoingTrip, Trip, TripLeg


def assign_sherpa(trip: Trip, sherpa: str, session: DBSession):
    ongoing_trip = session.create_ongoing_trip(sherpa, trip.id)
    trip.assign_sherpa(sherpa)
    get_logger(sherpa).info(f"assigned trip id {trip.id} to {sherpa}")
    return ongoing_trip


def start_trip(ongoing_trip: OngoingTrip, session: DBSession):
    ongoing_trip.trip.start()


def end_trip(ongoing_trip: OngoingTrip, success: bool, session: DBSession):
    ongoing_trip.trip.end(success)
    session.delete_ongoing_trip(ongoing_trip)


def start_leg(ongoing_trip: OngoingTrip, session: DBSession) -> TripLeg:
    trip: Trip = ongoing_trip.trip
    trip_leg: TripLeg = session.create_trip_leg(
        trip.id, trip.curr_station(), trip.next_station()
    )
    ongoing_trip.set_leg_id(trip_leg.id)
    trip.start_leg()
    sherpa_name = ongoing_trip.sherpa_name
    if trip.curr_station():
        update_leg_curr_station(trip.curr_station(), sherpa_name, session)
    update_leg_next_station(trip.next_station(), sherpa_name, session)
    update_leg_sherpa(sherpa_name, session)

    return trip_leg


def end_leg(trip_leg: TripLeg):
    trip_leg.end()
    trip_leg.trip.end_leg()


def update_leg_curr_station(curr_station_name: str, sherpa: str, session: DBSession):
    curr_station_status = session.get_station_status(curr_station_name)
    if not curr_station_status:
        return
    if sherpa in curr_station_status.arriving_sherpas():
        curr_station_status.arriving_sherpas.remove(sherpa)


def update_leg_next_station(next_station_name: str, sherpa: str, session: DBSession):
    next_station_status = session.get_station_status(next_station_name)
    if not next_station_status:
        return
    next_station_status.arriving_sherpas.append(sherpa)


def update_leg_sherpa(sherpa_name: str, session: DBSession):
    sherpa_status = session.get_sherpa_status(sherpa_name)
    sherpa_status.idle = False
