import logging
from typing import Union
from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse
from sqlalchemy.orm.attributes import flag_modified
import asyncio
import pandas as pd
from datetime import datetime, time, date
import io
import math

# ati code imports
import app.routers.dependencies as dpd
import models.request_models as rqm
import models.trip_models as tm
import models.misc_models as mm
from models.db_session import DBSession
from utils.util import str_to_dt, dt_to_str
import utils.trip_utils as tu
import core.constants as cc
import utils.util as utils_util
import core.common as ccm
from openpyxl import Workbook
from openpyxl.worksheet.page import PageMargins


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

    with DBSession(engine=ccm.engine) as dbsession:
        sherpa = dbsession.get_sherpa(sherpa_name)

        if sherpa.status.disabled_reason not in [
            cc.DisabledReason.STALE_HEARTBEAT,
            cc.DisabledReason.SOFTWARE_NOT_COMPATIBLE,
        ]:
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

    with DBSession(engine=ccm.engine) as dbsession:
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

    with DBSession(engine=ccm.engine) as dbsession:
        trips = dbsession.get_trip_with_booking_id(booking_id)
        paused_trip = dbsession.get_paused_trip_with_booking_id(booking_id)

        if paused_trip:
            dbsession.session.delete(paused_trip)
            return response
        
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


@router.post("/status/{type}")
async def trip_status_with_type(
    type: str,
    trip_status_req: rqm.TripStatusReq,
    user_name=Depends(dpd.get_user_from_header),
):
    response = {}

    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    valid_status = []
    if type == "yet_to_start":
        valid_status = tm.YET_TO_START_TRIP_STATUS
    elif type == "completed":
        valid_status = tm.COMPLETED_TRIP_STATUS
    elif type == "ongoing":
        valid_status = tm.ONGOING_TRIP_STATUS
    else:
        dpd.raise_error("Query sent for an invalid trip type")

    with DBSession(engine=ccm.engine) as dbsession:
        if trip_status_req.from_dt and trip_status_req.to_dt:
            trip_status_req.from_dt = str_to_dt(trip_status_req.from_dt)
            trip_status_req.to_dt = str_to_dt(trip_status_req.to_dt)

            all_trips = dbsession.get_trips_with_timestamp_and_status(
                trip_status_req.from_dt, trip_status_req.to_dt, valid_status
            )

        else:
            if not trip_status_req.trip_ids:
                return response

            all_trips = dbsession.get_trips_with_ids_and_status(
                trip_status_req.trip_ids, valid_status
            )
            # dpd.raise_error("no trip id given or available in the given timeframe")

        count = 0
        for trip in all_trips:
            response.update({trip.id: tu.get_trip_status(trip)})

            # introducing sleep to allow other endpoints to work simultaneously
            count = count + 1
            if count % 50 == 0:
                await asyncio.sleep(100e-3)

    return response


# returns trip status, i.e. the time slot of the trip booking and the trip status with timestamp.
@router.post("/status_pg/{type}")
async def trip_status_pg_with_type(
    type: str,
    trip_status_req: rqm.TripStatusReq_pg,
    user_name=Depends(dpd.get_user_from_header),
):
    response = {}

    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    valid_status = []
    if type == "yet_to_start" or type == "scheduled":
        valid_status = tm.YET_TO_START_TRIP_STATUS
    elif type == "completed":
        valid_status = tm.COMPLETED_TRIP_STATUS
    elif type == "ongoing":
        valid_status = tm.ONGOING_TRIP_STATUS
    elif type == "active":
        valid_status = tm.ACTIVE_TRIP_STATUS
    else:
        dpd.raise_error("Query sent for an invalid trip type")

    logging.getLogger("uvicorn").info(
        f"trip_status_req: {jsonable_encoder(trip_status_req)}"
    )

    with DBSession(engine=ccm.engine) as dbsession:
        if trip_status_req.from_dt and trip_status_req.to_dt:
            trip_status_req.from_dt = str_to_dt(trip_status_req.from_dt)
            trip_status_req.to_dt = str_to_dt(trip_status_req.to_dt)

        if type == "scheduled":
            response = dbsession.get_scheduled_trips(
                trip_status_req.filter_fleets,
                valid_status,
                trip_status_req.filter_status,
                trip_status_req.search_txt,
                trip_status_req.sort_field,
                trip_status_req.sort_order,
                trip_status_req.page_no,
                trip_status_req.rec_limit,
            )
        else:
            response = dbsession.get_trips_with_timestamp_and_status_pagination(
                trip_status_req.from_dt,
                trip_status_req.to_dt,
                trip_status_req.filter_fleets,
                valid_status,
                trip_status_req.filter_sherpa_names,
                trip_status_req.filter_status,
                trip_status_req.booked_by,
                trip_status_req.search_by_stations,
                trip_status_req.search_txt,
                trip_status_req.sort_field,
                trip_status_req.sort_order,
                trip_status_req.page_no,
                trip_status_req.rec_limit,
            )

    return response


@router.post("/status")
async def trip_status(
    trip_status_req: rqm.TripStatusReq, user_name=Depends(dpd.get_user_from_header)
):
    response = {}

    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    with DBSession(engine=ccm.engine) as dbsession:
        all_trips = None
        if trip_status_req.from_dt and trip_status_req.to_dt:
            trip_status_req.from_dt = str_to_dt(trip_status_req.from_dt)
            trip_status_req.to_dt = str_to_dt(trip_status_req.to_dt)
            all_trips = dbsession.get_trips_with_timestamp(
                trip_status_req.from_dt, trip_status_req.to_dt
            )

        else:
            if not trip_status_req.trip_ids:
                return response
            all_trips = dbsession.get_trips_with_ids(trip_status_req.trip_ids)

        count = 0
        for trip in all_trips:
            response.update({trip.id: tu.get_trip_status(trip)})
            count = count + 1

            # introducing sleep to allow other endpoints to work simultaneously
            if count % 50 == 0:
                await asyncio.sleep(100e-3)

    return response


# returns ongoing trip status.


@router.get("/ongoing_trip_status")
async def ongoing_trip_status(user_name=Depends(dpd.get_user_from_header)):
    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    response = {}
    with DBSession(engine=ccm.engine) as dbsession:
        all_ongoing_trips = dbsession.get_all_ongoing_trips()
        for ongoing_trip in all_ongoing_trips:
            response.update({ongoing_trip.trip_id: tu.get_trip_status(ongoing_trip.trip)})

    return response


# returns the complete analysis of the trip as in when it started, when it ended, when was it supposed to end
# performs analysis for every trip leg and also for the overall trip.


@router.post("/analytics_pg")
async def trip_analytics_pg(
    trip_analytics_req: rqm.TripStatusReq_pg, user_name=Depends(dpd.get_user_from_header)
):
    response = {}
    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    with DBSession(engine=ccm.engine) as dbsession:
        if trip_analytics_req.from_dt and trip_analytics_req.to_dt:
            trip_analytics_req.from_dt = str_to_dt(trip_analytics_req.from_dt)
            trip_analytics_req.to_dt = str_to_dt(trip_analytics_req.to_dt)

        trip_analytics = dbsession.get_trip_analytics_with_pagination(
            trip_analytics_req.from_dt,
            trip_analytics_req.to_dt,
            trip_analytics_req.filter_fleets,
            trip_analytics_req.filter_sherpa_names,
            trip_analytics_req.filter_status,
            trip_analytics_req.sort_field,
            trip_analytics_req.sort_order,
            trip_analytics_req.page_no,
            trip_analytics_req.rec_limit,
        )
        response = trip_analytics

    return response


@router.post("/analytics")
async def trip_analytics(
    trip_analytics_req: rqm.TripStatusReq, user_name=Depends(dpd.get_user_from_header)
):
    response = {}
    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    with DBSession(engine=ccm.engine) as dbsession:
        if trip_analytics_req.from_dt and trip_analytics_req.to_dt:
            trip_analytics_req.from_dt = str_to_dt(trip_analytics_req.from_dt)
            trip_analytics_req.to_dt = str_to_dt(trip_analytics_req.to_dt)

            all_trip_analytics = dbsession.get_trip_analytics_with_timestamp(
                trip_analytics_req.from_dt, trip_analytics_req.to_dt
            )

        else:
            if not trip_analytics_req.trip_ids:
                return response
                all_trip_analytics = dbsession.get_trip_analytics_with_trip_ids(
                    trip_analytics_req.trip_ids
                )
            # dpd.raise_error("no trip id given or available in the given timeframe")

        count = 0
        for trip_analytics in all_trip_analytics:
            response.update(
                {trip_analytics.trip_leg_id: tu.get_trip_analytics(trip_analytics)}
            )

            # introducing sleep to allow other endpoints to work simultaneously
            count = count + 1
            if count % 50 == 0:
                await asyncio.sleep(100e-3)

    return response


@router.post("/analytics_with_trip_info")
async def trip_analytics_with_trip_info(
    trip_analytics_req: rqm.TripAnalyticsWithTripInfoReq, user_name=Depends(dpd.get_user_from_header)
):
    response = {}
    if not user_name:
        dpd.raise_error("Unknown requester", 401)    

    with DBSession(engine=ccm.engine) as dbsession:
        all_trip_analytics = dbsession.get_trip_analytics_with_trips_info(
            trip_analytics_req.from_dt, trip_analytics_req.to_dt, trip_analytics_req.booked_by, trip_analytics_req.filter_fleets
        )
        response = all_trip_analytics

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

    with DBSession(engine=ccm.engine) as dbsession:
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

    with DBSession(engine=ccm.engine) as dbsession:
        trip: tm.Trip = dbsession.get_trip(trip_id)
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

    with DBSession(engine=ccm.engine) as dbsession:
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

    with DBSession(engine=ccm.engine) as dbsession:
        saved_routes = dbsession.get_saved_routes_fleet(fleet_name)

        for saved_route in saved_routes:
            used_by_backend = False
            update = False

            for _tag in mm.ConditionalTripTags:
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


@router.get("/get_saved_route/{route_tag}")
async def get_saved_route(route_tag: str, user_name=Depends(dpd.get_user_from_header)):
    response = {}
    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    with DBSession(engine=ccm.engine) as dbsession:
        saved_route = dbsession.get_saved_route(route_tag)

        if saved_route is None:
            dpd.raise_error(f"route with tag {route_tag} does not exist")

        response = utils_util.get_table_as_dict(tm.SavedRoutes, saved_route)

    return response


@router.delete("/delete_saved_route/{tag}")
async def delete_saved_route(tag: str, user_name=Depends(dpd.get_user_from_header)):
    response = {}
    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    with DBSession(engine=ccm.engine) as dbsession:
        saved_route = dbsession.get_saved_route(tag)

        if saved_route is None:
            dpd.raise_error(f"No saved route with tag:{tag}")

        can_edit = saved_route.other_info.get("can_edit", "False")

        if not eval(can_edit):
            dpd.raise_error("Cannot edit/delete this route tag, can_edit is set to False")

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

    with DBSession(engine=ccm.engine) as dbsession:
        saved_route = dbsession.get_saved_route(update_saved_route_req.tag)

        if saved_route is None:
            dpd.raise_error(f"No saved route with tag:{update_saved_route_req.tag}")

        if saved_route.other_info is None:
            saved_route.other_info = {}

        saved_route.other_info.update(update_saved_route_req.other_info)

        flag_modified(saved_route, "other_info")

    return response


@router.post("/export_all_analytics_data")
async def export_all_analytics_data(
    trip_analytics_req: rqm.TripAnalyticsReq,
    user_name=Depends(dpd.get_user_from_header)
):
    if not user_name:
        dpd.raise_error("Unknown requester", 401)
    response = {}
    with DBSession() as dbsession:
        if trip_analytics_req.start_time and trip_analytics_req.end_time:
            # Convert string dates to datetime objects
            trip_analytics_req.start_time = utils_util.str_to_dt(trip_analytics_req.start_time)
            trip_analytics_req.end_time = utils_util.str_to_dt(trip_analytics_req.end_time)
            all_trip_analytics = dbsession.get_trip_analytics_to_export(
                trip_analytics_req.start_time,
                trip_analytics_req.end_time,
                trip_analytics_req.fleet_name,
                trip_analytics_req.status,
                trip_analytics_req.sherpa_name,
                trip_analytics_req.sort_field,
                trip_analytics_req.sort_order,
            )
        else:
            dpd.raise_error("start_time and end_time are required")
        
        data = []
        for trip_analytic in all_trip_analytics:
            trip_analytic_legs = trip_analytic.get("legs")
            del trip_analytic["legs"]
        
            for trip_analytic_leg in trip_analytic_legs:
                processed_trip_data = {
                    "trip_id": trip_analytic.get("id"),
                    **trip_analytic,
                }
                del processed_trip_data["id"]

                trip_analytic_leg_details = {
                    **trip_analytic_leg,
                    "leg_route_length": trip_analytic_leg.pop("route_length", None),
                    "leg_start_time": trip_analytic_leg.pop("start_time", None),
                    "leg_end_time": trip_analytic_leg.pop("end_time", None),
                    "leg_created_at": trip_analytic_leg.pop("created_at", None),
                    "leg_updated_at": trip_analytic_leg.pop("updated_at", None),
                }
                if "sherpa_name" in trip_analytic_leg_details:
                    del trip_analytic_leg_details["sherpa_name"]
                if "trip_id" in trip_analytic_leg_details:
                    del trip_analytic_leg_details["trip_id"]

                processed_trip_data.update(trip_analytic_leg_details)

                processed_trip_data = utils_util.format_dates(processed_trip_data)
                data.append(processed_trip_data)
            if len(trip_analytic_legs) == 0:
                processed_trip_data = {
                    "trip_id": trip_analytic.get("id"),
                    **trip_analytic,
                }
                del processed_trip_data["id"]

                processed_trip_data = utils_util.format_dates(processed_trip_data)
                data.append(processed_trip_data)
             
        # Convert to DataFrame
        df = pd.DataFrame(data)

    # Convert DataFrame to CSV
    output = io.StringIO()
    df.to_csv(output, index=False)
    # Prepare the response
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),  # Convert string buffer to bytes
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=detail_analytics.csv"},
    )


@router.post("/pause_resume_schedule_trip")
async def pause_schedule_trip(
    pause_schedule_trip_req: rqm.PauseResumeScheduleTripReq,
    user_name=Depends(dpd.get_user_from_header),
):
    response = {}
    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    with DBSession(engine=ccm.engine) as dbsession:
        trips : tm.Trip = dbsession.get_trips_with_booking_id(pause_schedule_trip_req.booking_id)

        if trips is None:
            dpd.raise_error(f"Trip with booking id:{pause_schedule_trip_req.booking_id} does not exist")
        
        trip : tm.Trip = trips[-1]

        if trip.scheduled is False:
            dpd.raise_error(
                f"Trip with booking id:{pause_schedule_trip_req.booking_id} is not scheduled"
            )

        pause_trip = dbsession.get_paused_trip_with_booking_id(pause_schedule_trip_req.booking_id)
        
        if pause_schedule_trip_req.pause:
            if pause_trip is not None:
                dpd.raise_error(f"Trip with booking id:{pause_schedule_trip_req.booking_id} is already paused")
            
            new_trip_metadata = trip.trip_metadata
            if new_trip_metadata.get("total_trip_progress"):
                del new_trip_metadata["total_trip_progress"]
            dbsession.create_paused_trip(
                trip.route,
                trip.priority,
                new_trip_metadata,
                trip.booking_id,
                trip.fleet_name,
                trip.booked_by,
                trip.booking_time,
            )
            for t in trips:
                if t.status in tm.YET_TO_START_TRIP_STATUS:
                    delete_booked_trip_req: rqm.DeleteBookedTripReq = rqm.DeleteBookedTripReq(
                    booking_id=pause_schedule_trip_req.booking_id, trip_id=t.id)
                    response = await dpd.process_req_with_response(None, delete_booked_trip_req, user_name)
                if t.status in tm.ONGOING_TRIP_STATUS:
                    t.trip_metadata["scheduled_end_time"] = trip.trip_metadata["scheduled_start_time"]
                    flag_modified(t, "trip_metadata")
        else:
            if pause_trip is None:
                dpd.raise_error(f"Trip with booking id:{pause_schedule_trip_req.booking_id} is not paused")

            new_trip_metadata = pause_trip.trip_metadata
            new_trip_metadata = tu.modify_trip_metadata(new_trip_metadata)

            new_trip: tm.Trip = dbsession.create_trip(
                pause_trip.route,
                pause_trip.priority,
                new_trip_metadata,
                pause_trip.booking_id,
                pause_trip.fleet_name,
                pause_trip.booked_by,
            )
            dbsession.create_pending_trip(new_trip.id)
            dbsession.delete_paused_trip(pause_trip)

    return response