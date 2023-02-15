from typing import Union
from fastapi import APIRouter, Depends
from sqlalchemy.orm.attributes import flag_modified

from app.routers.dependencies import (
    get_user_from_header,
    process_req_with_response,
    raise_error,
)
import models.request_models as rqm
from models.trip_models import Trip, TripAnalytics
from models.db_session import DBSession
from utils.util import str_to_dt
import utils.trip_utils as tu


router = APIRouter(
    prefix="/api/v1/trips",
    tags=["trips"],
    responses={404: {"description": "Not found"}},
)

# to book, delete ongoing and pending trips, clear optimal dispatch assignments,
# posts trip status on the FM and also does trip analysis.


@router.post("/book")
async def book(booking_req: rqm.BookingReq, user_name=Depends(get_user_from_header)):
    response = process_req_with_response(None, booking_req, user_name)
    return response


@router.delete("/ongoing/{booking_id}")
async def delete_ongoing_trip(booking_id: int, user_name=Depends(get_user_from_header)):
    if not user_name:
        raise_error("Unknown requester", 401)

    with DBSession() as dbsession:
        trips = dbsession.get_trip_with_booking_id(booking_id)
        if not trips:
            raise_error("no trip with the given booking_id")

    delete_ongoing_trip_req: rqm.DeleteOngoingTripReq = rqm.DeleteOngoingTripReq(
        booking_id=booking_id
    )
    response = process_req_with_response(None, delete_ongoing_trip_req, user_name)

    return response


@router.delete("/booking/{booking_id}")
async def delete_pending_trip(booking_id: int, user_name=Depends(get_user_from_header)):

    response = {}
    if not user_name:
        raise_error("Unknown requester", 401)

    with DBSession() as dbsession:
        trips = dbsession.get_trip_with_booking_id(booking_id)

        if not trips:
            raise_error("no trip with the given booking_id")

    delete_booked_trip_req: rqm.DeleteBookedTripReq = rqm.DeleteBookedTripReq(
        booking_id=booking_id
    )
    response = process_req_with_response(None, delete_booked_trip_req, user_name)

    return response


# based on the trip bookings, optimal dispatch assigns the tasks to various sherpas optimally.
# deletes all the assignments done to the sherpas.


@router.get("/booking/{entity_name}/clear_optimal_dispatch_assignments")
async def clear_optimal_dispatch_assignments(
    entity_name=Union[str, None], user_name=Depends(get_user_from_header)
):

    response = {}

    if not user_name:
        raise_error("Unknown requester", 401)

    if not entity_name:
        raise_error("No entity name")

    delete_optimal_dispatch_assignments_req = rqm.DeleteOptimalDispatchAssignments(
        fleet_name=entity_name
    )

    response = process_req_with_response(
        None, delete_optimal_dispatch_assignments_req, user_name
    )

    return response


# returns trip status, i.e. the time slot of the trip booking and the trip status with timestamp.


@router.post("/status")
async def trip_status(
    trip_status_req: rqm.TripStatusReq, user_name=Depends(get_user_from_header)
):
    response = {}

    if not user_name:
        raise_error("Unknown requester", 401)

    with DBSession() as dbsession:
        if trip_status_req.booked_from and trip_status_req.booked_till:
            trip_status_req.booked_from = str_to_dt(trip_status_req.booked_from)
            trip_status_req.booked_till = str_to_dt(trip_status_req.booked_till)

            trip_status_req.trip_ids = dbsession.get_trip_ids_with_timestamp(
                trip_status_req.booked_from, trip_status_req.booked_till
            )

        if not trip_status_req.trip_ids:
            raise_error("no trip id given or available in the given timeframe")

        for trip_id in trip_status_req.trip_ids:
            trip: Trip = dbsession.get_trip(trip_id)
            if not trip:
                raise_error("invalid trip id")
            response.update({trip_id: tu.get_trip_status(trip)})

    return response


# returns ongoing trip status.


@router.get("/ongoing_trip_status")
async def ongoing_trip_status(user_name=Depends(get_user_from_header)):
    if not user_name:
        raise_error("Unknown requester", 401)

    response = {}
    with DBSession() as dbsession:
        all_ongoing_trips = dbsession.get_all_ongoing_trips()
        for ongoing_trip in all_ongoing_trips:
            response.update({ongoing_trip.trip_id: tu.get_trip_status(ongoing_trip.trip)})

    return response


# returns the complete analysis of the trip as in when it started, when it ended, when was it supposed to end
# performs analysis for every trip leg and also for the overall trip.


@router.post("/analytics")
async def trip_analytics(
    trip_analytics_req: rqm.TripStatusReq, user_name=Depends(get_user_from_header)
):

    response = {}
    if not user_name:
        raise_error("Unknown requester", 401)

    with DBSession() as dbsession:
        if trip_analytics_req.booked_from and trip_analytics_req.booked_till:
            trip_analytics_req.booked_from = str_to_dt(trip_analytics_req.booked_from)
            trip_analytics_req.booked_till = str_to_dt(trip_analytics_req.booked_till)

            trip_analytics_req.trip_ids = dbsession.get_trip_ids_with_timestamp(
                trip_analytics_req.booked_from, trip_analytics_req.booked_till
            )

        if not trip_analytics_req.trip_ids:
            raise_error("no trip id given or available in the given timeframe")

        for trip_id in trip_analytics_req.trip_ids:
            trip_legs_id = dbsession.get_all_trip_legs(trip_id)
            for trip_leg_id in trip_legs_id:
                trip_analytics: TripAnalytics = dbsession.get_trip_analytics(trip_leg_id)
                if not trip_analytics:
                    continue
                response.update({trip_leg_id: tu.get_trip_analytics(trip_analytics)})

    return response


@router.post("/{trip_id}/add_trip_metadata")
async def add_trip_metadata(
    trip_id: int,
    new_trip_metadata: rqm.TripMetaData,
    user_name=Depends(get_user_from_header),
):

    response = {}
    if not user_name:
        raise_error("Unknown requester", 401)

    with DBSession() as dbsession:
        trip: Trip = dbsession.get_trip(trip_id)
        if trip.trip_metadata is None:
            trip.trip_metadata = {}

        trip.trip_metadata.update(new_trip_metadata.metadata)
        flag_modified(trip, "trip_metadata")

    return response


@router.get("/{trip_id}/add_trip_description/{description}")
async def add_trip_description(
    trip_id: int, description: str, user_name=Depends(get_user_from_header)
):

    response = {}
    if not user_name:
        raise_error("Unknown requester", 401)

    with DBSession() as dbsession:
        trip: Trip = dbsession.get_trip(trip_id)
        if trip.trip_metadata is None:
            trip.trip_metadata = {}
        trip.trip_metadata.update({"description": description})
        flag_modified(trip, "trip_metadata")

    return response


def handle(handler, msg):
    handler.handle(msg)
