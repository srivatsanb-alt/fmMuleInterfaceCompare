from datetime import datetime, date
import math

from models.trip_models import Trip, OngoingTrip, TripAnalytics
from models.db_session import DBSession
from utils import util
from utils.util import get_table_as_dict

# utils for trips
# Donot modofiy - has other dependencies like Master FM Comms
# Master FM update_trip_inforequest model has to be in sync with this


def get_trip_status(trip: Trip):
    trip_status = {}
    with DBSession() as dbsession:
        ongoing_trip: OngoingTrip = dbsession.get_ongoing_trip_with_trip_id(trip.id)

        booking_time = None
        end_time = None
        start_time = None
        updated_at = None
        trip_leg = None
        trip_analytics = None

        if trip.booking_time:
            booking_time = util.dt_to_str(trip.booking_time)
        if trip.start_time:
            start_time = util.dt_to_str(trip.start_time)
        if trip.end_time:
            end_time = util.dt_to_str(trip.end_time)
        if trip.updated_at:
            updated_at = util.dt_to_str(trip.updated_at)

        if ongoing_trip:
            trip_leg = ongoing_trip.trip_leg
            trip_analytics: TripAnalytics = dbsession.get_trip_analytics(
                ongoing_trip.trip_leg_id
            )

        trip_details = {
            "status": trip.status,
            "route_lengths": trip.route_lengths,
            "etas_at_start": trip.etas_at_start,
            "etas": trip.etas,
            "trip_leg_id": trip_leg.id if trip_leg else None,
            "next_idx_aug": ongoing_trip.next_idx_aug if ongoing_trip else None,
            "trip_leg_from_station": trip_leg.from_station if trip_leg else None,
            "trip_leg_to_station": trip_leg.to_station if trip_leg else None,
            "trip_metadata": trip.trip_metadata,
            "route": trip.augmented_route,
            "priority": trip.priority,
            "scheduled": trip.scheduled,
            "time_period": trip.time_period,
            "booking_id": trip.booking_id,
            "booking_time": booking_time,
            "start_time": start_time,
            "end_time": end_time,
            "updated_at": updated_at,
            "booked_by": trip.booked_by,
        }

        # all clients need to change for duplicated trip leg details to be removed from trip_details
        # all_clients - summon button, sanjaya, conveyor, ies
        trip_leg_details = {
            "id": trip_leg.id if trip_leg else None,
            "status": trip_leg.status if trip_leg else None,
            "progress": trip_analytics.progress if trip_analytics else None,
            "route_length": trip_analytics.route_length if trip_analytics else None,
            "from_station": trip_leg.from_station if trip_leg else None,
            "to_station": trip_leg.to_station if trip_leg else None,
            "stoppage_reason": trip_leg.stoppage_reason if trip_leg else None,
        }

        trip_status = {
            "trip_id": trip.id,
            "sherpa_name": trip.sherpa_name,
            "fleet_name": trip.fleet_name,
            "trip_details": trip_details,
            "trip_leg_details": trip_leg_details,
        }

    return trip_status


def get_trip_analytics(trip_analytics: TripAnalytics):
    return get_table_as_dict(TripAnalytics, trip_analytics)

def modify_trip_metadata(trip_metadata):
    old_num_days_to_repeat = trip_metadata.get("num_days_to_repeat", None)
    old_scheduled_start_time = trip_metadata.get("scheduled_start_time", None)
    old_scheduled_time_period = int(trip_metadata.get("scheduled_time_period", None))
    if old_num_days_to_repeat != '0':

        trip_metadata["scheduled_start_time"] = update_to_current_date(trip_metadata["scheduled_start_time"])
        trip_metadata["scheduled_end_time"] = update_to_current_date(trip_metadata["scheduled_end_time"])
    else:
        start = util.str_to_dt(old_scheduled_start_time)
        unix_time = int(start.timestamp())
        end = datetime.now()
        difference = end - start 
        seconds = difference.total_seconds()
        unix_timestamp = (unix_time + math.ceil(seconds/old_scheduled_time_period)*old_scheduled_time_period)
        dt_object = datetime.fromtimestamp(unix_timestamp)
        dt_str = util.dt_to_str(dt_object)
        trip_metadata["scheduled_start_time"] = dt_str

    return trip_metadata

def update_to_current_date(timestamp_str):
    dt = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
    current_date = date.today()
    if dt.date() <= current_date:
        updated_dt = dt.replace(year=current_date.year, month=current_date.month, day=current_date.day)
        updated_timestamp = updated_dt.strftime("%Y-%m-%d %H:%M:%S")    
        return updated_timestamp
    return timestamp_str

