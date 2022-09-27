from models.trip_models import Trip, OngoingTrip
from models.db_session import session
import datetime


def get_trip_status(trip: Trip):
    ongoing_trip: OngoingTrip = session.get_ongoing_trip_with_trip_id(trip.id)
    booking_time = None
    end_time = None
    start_time = None
    updated_at = None
    trip_leg = None

    if trip.booking_time:
        booking_time = datetime.datetime.strftime(trip.booking_time, "%Y-%m-%d %H:%M:%S")
    if trip.start_time:
        start_time = datetime.datetime.strftime(trip.start_time, "%Y-%m-%d %H:%M:%S")
    if trip.end_time:
        end_time = datetime.datetime.strftime(trip.end_time, "%Y-%m-%d %H:%M:%S")

    if trip.updated_at:
        updated_at = datetime.datetime.strftime(trip.updated_at, "%Y-%m-%d %H:%M:%S")

    if ongoing_trip:
        trip_leg = session.get_trip_leg(ongoing_trip.sherpa_name)

    trip_details = {
        "status": trip.status,
        "eta_at_start": None,
        "eta": None,
        "trip_leg_id": trip_leg.id if trip_leg else None,
        "trip_leg_from_station": trip_leg.from_station if trip_leg else None,
        "trip_leg_to_station": trip_leg.to_station if trip_leg else None,
        "route": trip.augmented_route,
        "priority": trip.priority,
        "milkrun": trip.milkrun,
        "booking_id": trip.booking_id,
        "booking_time": booking_time,
        "start_time": start_time,
        "end_time": end_time,
        "updated_at": updated_at,
    }

    trip_status = {
        "trip_id": trip.id,
        "sherpa_name": trip.sherpa_name,
        "fleet_name": trip.fleet_name,
        "trip_details": trip_details,
    }

    return trip_status
