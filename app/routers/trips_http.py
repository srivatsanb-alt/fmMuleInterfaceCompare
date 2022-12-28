import pandas as pd
from typing import Union
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from app.routers.dependencies import (
    get_user_from_header,
    process_req_with_response,
    close_session_and_raise_error,
    close_session,
)

from typing import Union
from fastapi import APIRouter, Depends
from models.request_models import (
    BookingReq,
    TripStatusReq,
    DeleteOngoingTripReq,
    DeleteBookedTripReq,
    DeleteOptimalDispatchAssignments,
)

from models.trip_models import Trip, TripAnalytics
from models.db_session import session
from utils.util import str_to_dt
import utils.trip_utils as tu

router = APIRouter(
    prefix="/api/v1/trips",
    tags=["trips"],
    responses={404: {"description": "Not found"}},
)


@router.post("/book")
async def book(booking_req: BookingReq, user_name=Depends(get_user_from_header)):
    response = process_req_with_response(None, booking_req, user_name)
    return response


@router.delete("/ongoing/{booking_id}")
async def delete_ongoing_trip(booking_id: int, user_name=Depends(get_user_from_header)):
    if not user_name:
        close_session_and_raise_error(session, "Unknown requester")

    trips = session.get_trip_with_booking_id(booking_id)

    if not trips:
        close_session_and_raise_error(session, "no trip with the given booking_id")

    delete_ongoing_trip_req: DeleteOngoingTripReq = DeleteOngoingTripReq(
        booking_id=booking_id
    )

    close_session(session)
    response = process_req_with_response(None, delete_ongoing_trip_req, user_name)

    return response


@router.delete("/booking/{booking_id}")
async def delete_pending_trip(booking_id: int, user_name=Depends(get_user_from_header)):

    response = {}
    if not user_name:
        close_session_and_raise_error(session, "Unknown requester")

    trips = session.get_trip_with_booking_id(booking_id)

    if not trips:
        close_session_and_raise_error(session, "no trip with the given booking_id")

    delete_booked_trip_req: DeleteBookedTripReq = DeleteBookedTripReq(booking_id=booking_id)

    close_session(session)
    response = process_req_with_response(None, delete_booked_trip_req, user_name)

    return response


@router.get("/booking/{entity_name}/clear_optimal_dispatch_assignments")
async def clear_optimal_dispatch_assignments(
    entity_name=Union[str, None], user_name=Depends(get_user_from_header)
):

    response = {}

    if not user_name:
        close_session_and_raise_error(session, "Unknown requester")

    if not entity_name:
        close_session_and_raise_error(session, "No entity name")

    delete_optimal_dispatch_assignments_req = DeleteOptimalDispatchAssignments(
        fleet_name=entity_name
    )

    close_session(session)
    response = process_req_with_response(
        None, delete_optimal_dispatch_assignments_req, user_name
    )

    return response


@router.post("/status")
async def trip_status(
    trip_status_req: TripStatusReq, user_name=Depends(get_user_from_header)
):
    if not user_name:
        close_session_and_raise_error(session, "Unknown requester")

    response = {}
    if trip_status_req.booked_from and trip_status_req.booked_till:
        trip_status_req.booked_from = str_to_dt(trip_status_req.booked_from)
        trip_status_req.booked_till = str_to_dt(trip_status_req.booked_till)

        trip_status_req.trip_ids = session.get_trip_ids_with_timestamp(
            trip_status_req.booked_from, trip_status_req.booked_till
        )

    if not trip_status_req.trip_ids:
        close_session_and_raise_error(
            session, "no trip id given or available in the given timeframe"
        )

    for trip_id in trip_status_req.trip_ids:
        trip: Trip = session.get_trip(trip_id)
        if not trip:
            close_session_and_raise_error(session, "invalid trip id")
        response.update({trip_id: tu.get_trip_status(trip)})

    close_session(session)
    return response


@router.get("/ongoing_trip_status")
async def ongoing_trip_status(user_name=Depends(get_user_from_header)):
    if not user_name:
        close_session_and_raise_error(session, "Unknown requester")

    response = {}
    all_ongoing_trips = session.get_all_ongoing_trips()

    for ongoing_trip in all_ongoing_trips:
        response.update({ongoing_trip.trip_id: tu.get_trip_status(ongoing_trip.trip)})

    close_session(session)
    return response


@router.post("/analytics")
async def trip_analytics(
    trip_analytics_req: TripStatusReq, user_name=Depends(get_user_from_header)
):
    if not user_name:
        close_session_and_raise_error(session, "Unknown requester")

    response = {}
    if trip_analytics_req.booked_from and trip_analytics_req.booked_till:
        trip_analytics_req.booked_from = str_to_dt(trip_analytics_req.booked_from)
        trip_analytics_req.booked_till = str_to_dt(trip_analytics_req.booked_till)

        trip_analytics_req.trip_ids = session.get_trip_ids_with_timestamp(
            trip_analytics_req.booked_from, trip_analytics_req.booked_till
        )

    if not trip_analytics_req.trip_ids:
        close_session_and_raise_error(
            session, "no trip id given or available in the given timeframe"
        )

    for trip_id in trip_analytics_req.trip_ids:
        trip_legs_id = session.get_all_trip_legs(trip_id)
        for trip_leg_id in trip_legs_id:
            trip_analytics: TripAnalytics = session.get_trip_analytics(trip_leg_id)
            if not trip_analytics:
                continue
            response.update({trip_leg_id: tu.get_trip_analytics(trip_analytics)})

    close_session(session)
    return response


def handle(handler, msg):
    handler.handle(msg)
