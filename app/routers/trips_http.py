from app.routers.dependencies import (
    get_user_from_header,
    process_req_with_response,
)
from fastapi import APIRouter, Depends, HTTPException
from models.request_models import BookingReq, TripStatusReq, DeleteTripReq
from models.trip_models import TripStatus, PendingTrip, Trip, TripAnalytics
from fastapi.responses import HTMLResponse
from models.db_session import session
from utils.util import str_to_dt
import utils.trip_utils as tu
import pandas as pd

router = APIRouter(
    prefix="/api/v1/trips",
    tags=["trips"],
    responses={404: {"description": "Not found"}},
)


@router.post("/book/")
async def book(booking_req: BookingReq, user_name=Depends(get_user_from_header)):
    response = process_req_with_response(None, booking_req, user_name)
    return response


@router.delete("/ongoing/{booking_id}")
async def delete_ongoing_trip(booking_id: int, user_name=Depends(get_user_from_header)):
    if not user_name:
        raise HTTPException(status_code=403, detail="Unknown requester")

    delete_trip_req: DeleteTripReq = DeleteTripReq(booking_id=booking_id)
    response = process_req_with_response(None, delete_trip_req, user_name)
    return response


@router.delete("/booking/{booking_id}")
async def delete_pending_trip(booking_id: int, user_name=Depends(get_user_from_header)):

    response = {}
    if not user_name:
        raise HTTPException(status_code=403, detail="Unknown requester")

    trips = session.get_trip_with_booking_id(booking_id)
    if not trips:
        raise HTTPException(status_code=403, detail="no trip with the given booking_id")

    for trip in trips:
        if trip.status in [TripStatus.BOOKED, TripStatus.ASSIGNED]:
            raise HTTPException(
                status_code=403, detail="expected trip status to be booked or assigned"
            )

        pending_trip: PendingTrip = session.get_pending_trip_with_trip_id(trip.id)
        session.delete_pending_trip(pending_trip)
        trip.status = TripStatus.CANCELLED
        session.close()

    return response


@router.post("/status")
async def trip_status(
    trip_status_req: TripStatusReq, user_name=Depends(get_user_from_header)
):
    if not user_name:
        raise HTTPException(status_code=403, detail="Unknown requester")

    response = {}
    if trip_status_req.booked_from and trip_status_req.booked_till:
        trip_status_req.booked_from = str_to_dt(trip_status_req.booked_from)
        trip_status_req.booked_till = str_to_dt(trip_status_req.booked_till)

        trip_status_req.trip_ids = session.get_trip_ids_with_timestamp(
            trip_status_req.booked_from, trip_status_req.booked_till
        )

    if not trip_status_req.trip_ids:
        raise HTTPException(
            status_code=403,
            detail="no trip id given or available in the given timeframe",
        )

    for trip_id in trip_status_req.trip_ids:
        trip: Trip = session.get_trip(trip_id)
        if not trip:
            raise HTTPException(status_code=403, detail="invalid trip id")
        response.update({trip_id: tu.get_trip_status(trip)})
    return response


@router.post("/analytics")
async def trip_analytics(
    trip_analytics_req: TripStatusReq, user_name=Depends(get_user_from_header)
):
    if not user_name:
        raise HTTPException(status_code=403, detail="Unknown requester")

    response = {}
    if trip_analytics_req.booked_from and trip_analytics_req.booked_till:
        trip_analytics_req.booked_from = str_to_dt(trip_analytics_req.booked_from)
        trip_analytics_req.booked_till = str_to_dt(trip_analytics_req.booked_till)

        trip_analytics_req.trip_ids = session.get_trip_ids_with_timestamp(
            trip_analytics_req.booked_from, trip_analytics_req.booked_till
        )

    if not trip_analytics_req.trip_ids:
        raise HTTPException(
            status_code=403,
            detail="no trip id given or available in the given timeframe",
        )

    for trip_id in trip_analytics_req.trip_ids:
        trip_legs_id = session.get_all_trip_legs(trip_id)
        for trip_leg_id in trip_legs_id:
            trip_analytics: TripAnalytics = session.get_trip_analytics(trip_leg_id)

            # any trip_leg where from_station and to_station are same won't have trip leg
            if not trip_analytics:
                continue
            response.update({trip_leg_id: tu.get_trip_analytics(trip_analytics)})

    return response


# debug tool
# temporary addition for first release
# TODO : remove viewable code after frontend is enabled to read trips table
@router.get("/status/{num_trips}/{viewable}")
def get_last_n_trip_status(num_trips: int, viewable: int):
    response = {}
    trips = session.get_last_n_trips(num_trips)
    trip_ids = [trip.id for trip in trips]

    if not trip_ids:
        raise HTTPException(status_code=403, detail="bad request, no trip_ids")

    for trip_id in trip_ids:
        trip: Trip = session.get_trip(trip_id)
        if not trip:
            raise HTTPException(status_code=403, detail="invalid trip id")

        response.update({trip_id: tu.get_trip_status(trip)})

    if viewable:
        df = pd.DataFrame(data=response)
        df = df.fillna(" ")
        response = df.to_html()
        return HTMLResponse(content=response, status_code=200)

    return response


def handle(handler, msg):
    handler.handle(msg)
