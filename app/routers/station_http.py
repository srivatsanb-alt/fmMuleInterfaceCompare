from fastapi import APIRouter, Depends


# ati code imports
import models.fleet_models as fm
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
