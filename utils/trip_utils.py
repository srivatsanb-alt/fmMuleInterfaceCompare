from models.trip_models import Trip, OngoingTrip, TripAnalytics
from models.db_session import session
from utils import util
from utils.fleet_utils import get_table_as_dict


def get_trip_status(trip: Trip):
    ongoing_trip: OngoingTrip = session.get_ongoing_trip_with_trip_id(trip.id)

    booking_time = None
    end_time = None
    start_time = None
    updated_at = None
    trip_leg = None
    if trip.booking_time:
        booking_time = util.dt_to_str(trip.booking_time)
    if trip.start_time:
        start_time = util.dt_to_str(trip.start_time)
    if trip.end_time:
        end_time = util.dt_to_str(trip.end_time)
    if trip.updated_at:
        updated_at = util.dt_to_str(trip.updated_at)

    if ongoing_trip:
        trip_leg = session.get_trip_leg(ongoing_trip.sherpa_name)

    trip_details = {
        "status": trip.status,
        "etas_at_start": trip.etas_at_start,
        "trip_leg_id": trip_leg.id if trip_leg else None,
        "trip_leg_from_station": trip_leg.from_station if trip_leg else None,
        "trip_leg_to_station": trip_leg.to_station if trip_leg else None,
        "route": trip.augmented_route,
        "priority": trip.priority,
        "scheduled": trip.scheduled,
        "time_period": trip.time_period,
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


def get_trip_analytics(trip_analytics: TripAnalytics):
    return get_table_as_dict(TripAnalytics, trip_analytics)
