from typing import Union
from fastapi import APIRouter, Depends
from sqlalchemy.orm.attributes import flag_modified

# ati code imports
import app.routers.dependencies as dpd
import models.request_models as rqm
import models.trip_models as tm
from models.db_session import DBSession
from utils.util import str_to_dt
import utils.trip_utils as tu
import core.constants as cc


router = APIRouter(
    prefix="/api/v1/trips",
    tags=["trips"],
    responses={404: {"description": "Not found"}},
)

# to book, delete ongoing and pending trips, clear optimal dispatch assignments,
# posts trip status on the FM and also does trip analysis.


@router.post("/book")
async def book(booking_req: rqm.BookingReq, user_name=Depends(dpd.get_user_from_header)):
    response = await dpd.process_req_with_response(None, booking_req, user_name)
    return response


@router.delete("/force_delete/ongoing/{sherpa_name}")
async def force_delete_ongoing_trip(
    sherpa_name: str, user_name=Depends(dpd.get_user_from_header)
):
    response = {}

    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    with DBSession() as dbsession:
        sherpa = dbsession.get_sherpa(sherpa_name)

        if sherpa.status.disabled_reason != cc.DisabledReason.STALE_HEARTBEAT:
            dpd.raise_error("This option can be used only if the sherpa is disconnected")

        if sherpa.status.trip_id is None:
            dpd.raise_error(f"{sherpa_name} has no ongoing trip")

    force_delete_ongoing_trip_req = rqm.ForceDeleteOngoingTripReq(sherpa_name=sherpa_name)

    response = await dpd.process_req_with_response(
        None, force_delete_ongoing_trip_req, user_name
    )

    return response


@router.delete("/ongoing/{booking_id}/{trip_id}")
async def delete_ongoing_trip(
    booking_id: int, trip_id: int, user_name=Depends(dpd.get_user_from_header)
):
    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    with DBSession() as dbsession:
        trips = dbsession.get_trip_with_booking_id(booking_id)
        if not trips:
            dpd.raise_error("no trip with the given booking_id")

        if trip_id == -1:
            delete_ongoing_trip_req: rqm.DeleteOngoingTripReq = rqm.DeleteOngoingTripReq(
                booking_id=booking_id
            )
        else:
            valid_trip_id = False
            for trip in trips:
                if trip_id == trip.id:
                    valid_trip_id = True

            if not valid_trip_id:
                dpd.raise_error(
                    f"Invalid detail, no trip (trip_id: {trip_id}) for booking_id: {booking_id}"
                )
            delete_ongoing_trip_req: rqm.DeleteOngoingTripReq = rqm.DeleteOngoingTripReq(
                booking_id=booking_id, trip_id=trip_id
            )

    response = await dpd.process_req_with_response(None, delete_ongoing_trip_req, user_name)

    return response


@router.delete("/booking/{booking_id}/{trip_id}")
async def delete_pending_trip(
    booking_id: int, trip_id: int, user_name=Depends(dpd.get_user_from_header)
):

    response = {}
    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    with DBSession() as dbsession:
        trips = dbsession.get_trip_with_booking_id(booking_id)

        if not trips:
            dpd.raise_error("no trip with the given booking_id")

        if trip_id == -1:
            delete_booked_trip_req: rqm.DeleteBookedTripReq = rqm.DeleteBookedTripReq(
                booking_id=booking_id
            )

        else:
            valid_trip_id = False
            for trip in trips:
                if trip_id == trip.id:
                    valid_trip_id = True

            if not valid_trip_id:
                dpd.raise_error(
                    f"Invalid detail, no pending trip (trip_id: {trip_id}) for booking_id: {booking_id}"
                )

            delete_booked_trip_req: rqm.DeleteBookedTripReq = rqm.DeleteBookedTripReq(
                booking_id=booking_id, trip_id=trip_id
            )

    response = await dpd.process_req_with_response(None, delete_booked_trip_req, user_name)

    return response


# based on the trip bookings, optimal dispatch assigns the tasks to various sherpas optimally.
# deletes all the assignments done to the sherpas.


@router.get("/booking/{entity_name}/clear_optimal_dispatch_assignments")
async def clear_optimal_dispatch_assignments(
    entity_name=Union[str, None], user_name=Depends(dpd.get_user_from_header)
):

    response = {}

    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    if not entity_name:
        dpd.raise_error("No entity name")

    delete_optimal_dispatch_assignments_req = rqm.DeleteOptimalDispatchAssignments(
        fleet_name=entity_name
    )

    response = await dpd.process_req_with_response(
        None, delete_optimal_dispatch_assignments_req, user_name
    )

    return response


# returns trip status, i.e. the time slot of the trip booking and the trip status with timestamp.


@router.post("/status")
async def trip_status(
    trip_status_req: rqm.TripStatusReq, user_name=Depends(dpd.get_user_from_header)
):
    response = {}

    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    with DBSession() as dbsession:
        if trip_status_req.booked_from and trip_status_req.booked_till:
            trip_status_req.booked_from = str_to_dt(trip_status_req.booked_from)
            trip_status_req.booked_till = str_to_dt(trip_status_req.booked_till)

            trip_status_req.trip_ids = dbsession.get_trip_ids_with_timestamp(
                trip_status_req.booked_from, trip_status_req.booked_till
            )

        if not trip_status_req.trip_ids:
            return response
            # dpd.raise_error("no trip id given or available in the given timeframe")

        for trip_id in trip_status_req.trip_ids:
            trip: tm.Trip = dbsession.get_trip(trip_id)
            if not trip:
                dpd.raise_error("invalid trip id")
            response.update({trip_id: tu.get_trip_status(trip)})

    return response


# returns ongoing trip status.


@router.get("/ongoing_trip_status")
async def ongoing_trip_status(user_name=Depends(dpd.get_user_from_header)):
    if not user_name:
        dpd.raise_error("Unknown requester", 401)

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
    trip_analytics_req: rqm.TripStatusReq, user_name=Depends(dpd.get_user_from_header)
):

    response = {}
    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    with DBSession() as dbsession:
        if trip_analytics_req.booked_from and trip_analytics_req.booked_till:
            trip_analytics_req.booked_from = str_to_dt(trip_analytics_req.booked_from)
            trip_analytics_req.booked_till = str_to_dt(trip_analytics_req.booked_till)

            trip_analytics_req.trip_ids = dbsession.get_trip_ids_with_timestamp(
                trip_analytics_req.booked_from, trip_analytics_req.booked_till
            )

        if not trip_analytics_req.trip_ids:
            return response
            # dpd.raise_error("no trip id given or available in the given timeframe")

        for trip_id in trip_analytics_req.trip_ids:
            trip_legs_id = dbsession.get_all_trip_legs(trip_id)
            for trip_leg_id in trip_legs_id:
                trip_analytics: tm.TripAnalytics = dbsession.get_trip_analytics(trip_leg_id)
                if not trip_analytics:
                    continue
                response.update({trip_leg_id: tu.get_trip_analytics(trip_analytics)})

    return response


@router.post("/{trip_id}/add_trip_metadata")
async def add_trip_metadata(
    trip_id: int,
    new_trip_metadata: rqm.TripMetaData,
    user_name=Depends(dpd.get_user_from_header),
):

    response = {}
    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    with DBSession() as dbsession:
        trip: tm.Trip = dbsession.get_trip(trip_id)
        if trip.trip_metadata is None:
            trip.trip_metadata = {}

        trip.trip_metadata.update(new_trip_metadata.metadata)
        flag_modified(trip, "trip_metadata")

    return response


@router.get("/{trip_id}/add_trip_description/{description}")
async def add_trip_description(
    trip_id: int, description: str, user_name=Depends(dpd.get_user_from_header)
):

    response = {}
    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    with DBSession() as dbsession:
        trip: Trip = dbsession.get_trip(trip_id)
        if trip.trip_metadata is None:
            trip.trip_metadata = {}
        trip.trip_metadata.update({"description": description})
        flag_modified(trip, "trip_metadata")

    return response


@router.get("/popular_route/{fleet_name}/{num_routes}")
async def populate_route(
    fleet_name: str,
    num_routes: int,
    user_name=Depends(dpd.get_user_from_header),
):

    response = []

    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    with DBSession() as dbsession:
        populate_routes = dbsession.get_popular_routes(fleet_name)

    for route in populate_routes[:num_routes]:
        response.extend(route)

    return response


@router.post("/save_route")
async def save_route(
    save_route_req: rqm.SaveRouteReq, user_name=Depends(dpd.get_user_from_header)
):
    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    response = await dpd.process_req_with_response(None, save_route_req, user_name)

    return response


@router.get("/get_saved_routes/{fleet_name}/{backend_usage}")
async def get_saved_routes(
    fleet_name: str, backend_usage: bool, user_name=Depends(dpd.get_user_from_header)
):
    response = {}
    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    with DBSession() as dbsession:
        _tags = ["exclude_stations", "battery_swap", "idling"]
        saved_routes = dbsession.get_saved_routes_fleet(fleet_name)

        for saved_route in saved_routes:
            used_by_backend = False
            update = False
            for _tag in _tags:
                if _tag in saved_route.tag:
                    used_by_backend = True

            if used_by_backend and backend_usage:
                update = True
            elif not used_by_backend and not backend_usage:
                update = True

            if update:
                response.update(
                    {
                        saved_route.tag: {
                            "route": saved_route.route,
                            "fleet_name": saved_route.fleet_name,
                            "other_info": saved_route.other_info,
                        }
                    }
                )

    return response


@router.delete("/delete_saved_route/{tag}")
async def delete_saved_route(tag: str, user_name=Depends(dpd.get_user_from_header)):
    response = {}
    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    with DBSession() as dbsession:
        saved_route = dbsession.get_saved_route(tag)

        if saved_route is None:
            dpd.raise_error(f"No saved route with tag:{tag}")

        dbsession.session.delete(saved_route)

    return response


@router.post("/update_saved_route_info")
async def update_saved_route_metadata(
    update_saved_route_req: rqm.UpdateSavedRouteReq,
    user_name=Depends(dpd.get_user_from_header),
):
    response = {}
    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    with DBSession() as dbsession:
        saved_route = dbsession.get_saved_route(update_saved_route_req.tag)

        if saved_route is None:
            dpd.raise_error(f"No saved route with tag:{update_saved_route_req.tag}")

        if saved_route.other_info is None:
            saved_route.other_info = {}

        saved_route.other_info.update(update_saved_route_req.other_info)

        flag_modified(saved_route, "other_info")

    return response
