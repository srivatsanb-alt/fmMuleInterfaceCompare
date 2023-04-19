from fastapi import APIRouter, Depends
from typing import List

# ati code imports
import models.fleet_models as fm
import models.trip_models as tm
from models.base_models import StationProperties
from models.db_session import DBSession
import app.routers.dependencies as dpd


router = APIRouter(
    prefix="/api/v1/station",
    tags=["sherpa"],
    # dependencies=[Depends(get_sherpa)],
    responses={404: {"description": "Not found"}},
)


# FM gets station info
@router.get("/{entity_name}/info")
async def get_station_info(entity_name: str, user_name=Depends(dpd.get_user_from_header)):
    response = {}

    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    if not entity_name:
        dpd.raise_error("No entity name")

    with DBSession() as dbsession:
        station_status: fm.StationStatus = dbsession.get_station_status(entity_name)
        if not station_status:
            dpd.raise_error("Bad station name")

        station_props = [
            StationProperties(prop).name for prop in station_status.station.properties
        ]
        station_info = {
            "station_name": entity_name,
            "disabled": station_status.disabled,
            "fleet_name": station_status.station.fleet.name,
            "properties": station_props,
            "pose": station_status.station.pose,
        }
        response.update(station_info)

    return response


@router.get("/{entity_name}/disable/{disable}")
async def disable_station(
    entity_name: str, disable: bool, user_name=Depends(dpd.get_user_from_header)
):
    response = {}

    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    if not entity_name:
        dpd.raise_error("Bad detail")

    with DBSession() as dbsession:
        if disable:
            all_ongoing_trips: List[tm.OngoingTrip] = dbsession.get_all_ongoing_trips()
            for ongoing_trip in all_ongoing_trips:
                trip: tm.Trip = ongoing_trip.trip
                stations = trip.route
                if entity_name in stations:
                    raise ValueError(
                        f"Cannot disable station :{entity_name} ,ongoing trip : {trip.id} with station : {entity_name} in trip route : {trip.route}"
                    )

        station_status: fm.StationStatus = dbsession.get_station_status(entity_name)
        if not station_status:
            dpd.raise_error("Invalid station name")

        station_status.disabled = disable

    return response
