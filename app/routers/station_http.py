from app.routers.dependencies import (
    get_user_from_header,
    close_session_and_raise_error,
    close_session,
)
from models.fleet_models import StationStatus
from models.base_models import StationProperties
from fastapi import APIRouter, Depends
from models.db_session import session


router = APIRouter(
    prefix="/api/v1/station",
    tags=["sherpa"],
    # dependencies=[Depends(get_sherpa)],
    responses={404: {"description": "Not found"}},
)


@router.get("/{entity_name}/info")
async def get_station_info(entity_name: str, user_name=Depends(get_user_from_header)):
    response = {}

    if not user_name:
        close_session_and_raise_error(session, "Unknown requester")

    if not entity_name:
        close_session_and_raise_error(session, "No entity name")

    station_status: StationStatus = session.get_station_status(entity_name)

    if not station_status:
        close_session_and_raise_error(session, "Bad station name")

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

    close_session(session)
    return response
