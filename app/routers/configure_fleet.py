import os
import logging
from fastapi import APIRouter, Depends
from typing import Union
from models.db_session import DBSession
from utils import fleet_utils as fu
from utils.comms import close_websocket_for_sherpa
from models.fleet_models import (
    Fleet,
    Sherpa,
    SherpaStatus,
    AvailableSherpas,
    Station,
    StationStatus,
    MapFile,
    Map,
)
from app.routers.dependencies import (
    get_user_from_header,
    raise_error,
)

#manages the overall configuration of fleet by- deleting sherpa, fleet, map, station; update map.

# setup logging
log_conf_path = os.path.join(os.getenv("FM_CONFIG_DIR"), "logging.conf")
logging.config.fileConfig(log_conf_path)
logger = logging.getLogger("uvicorn")

#deletes sherpa

def delete_sherpa(dbsession, sherpa_name):

    logger.info(f"Will try deleting the sherpa {sherpa_name}")
    # close ws connection

    close_websocket_for_sherpa(sherpa_name)

    # delete sherpa status
    sherpa_status: SherpaStatus = dbsession.get_sherpa_status(sherpa_name)

    if not sherpa_status:
        raise_error("Bad detail invalid sherpa name")

    if sherpa_status.inducted:
        raise_error("Cannot delete sherpa that is enabled for trips")

    if sherpa_status.trip_id:
        trip = dbsession.get_trip(sherpa_status.trip_id)
        raise_error(
            f"delete the ongoing trip with booking_id: {trip.booking_id} to delete sherpa {sherpa_name}"
        )

    dbsession.session.delete(sherpa_status)

    # delete sherpa
    sherpa: Sherpa = dbsession.get_sherpa(sherpa_name)
    dbsession.session.delete(sherpa)

    # delete sherpa entry in AvailableSherpas
    dbsession.session.query(AvailableSherpas).filter(
        AvailableSherpas.sherpa_name == sherpa_name
    ).delete()

    logger.info(f"Successfully deleted {sherpa_name} from DB")

#deletes station from FM.

def delete_station(dbsession, station_name):

    logger.info(f"Will try deleting the station {station_name}")

    # delete sherpa status
    station_status: StationStatus = dbsession.get_station_status(station_name)

    dbsession.session.delete(station_status)

    # delete sherpa
    station: Station = dbsession.get_station(station_name)
    dbsession.session.delete(station)

    logger.info(f"Successfully deleted station {station_name} from DB")

#deletes map from FM.

def delete_map(dbsession, map_id):

    logger.info(f"Will try deleting map files with map_id: {map_id}")

    dbsession.session.query(MapFile).filter(MapFile.map_id == map_id).delete()
    dbsession.session.query(Map).filter(Map.id == map_id).delete()
    logger.info(f"Successfully deleted map with map_id: {map_id}")


router = APIRouter(
    prefix="/api/v1/configure_fleet",
    tags=["configure_fleet"],
    responses={404: {"description": "Not found"}},
)

#updates map on FM.

@router.get("/update_map/{fleet_name}")
async def update_map(
    fleet_name=Union[str, None],
    username=Depends(get_user_from_header),
):
    response = {}
    fleet_name = fleet_name

    if not username:
        raise_error("Unknown requester", 401)

    if not fleet_name:
        raise_error("No fleet name")

    with DBSession() as dbsession:

        all_ongoing_trips_fleet = dbsession.get_all_ongoing_trips_fleet(fleet_name)
        if len(all_ongoing_trips_fleet):
            raise_error("Cancel all the ongoing trips before resetting the fleet")

        fleet: Fleet = dbsession.get_fleet(fleet_name)

        if not fleet:
            raise_error("Bad detail invalid fleet name")

        fu.update_map(dbsession, fleet_name)
        all_fleet_sherpas = dbsession.get_all_sherpas_in_fleet(fleet_name)

        # close ws connection to make sure new map files are downloaded by sherpa on reconnect
        for sherpa in all_fleet_sherpas:
            close_websocket_for_sherpa(sherpa.name)

    return response

#deletes fleet from FM.

@router.get("/delete/fleet/{fleet_name}")
async def delete_fleet(
    fleet_name=Union[str, None],
    username=Depends(get_user_from_header),
):
    response = {}
    fleet_name = fleet_name

    if not username:
        raise_error("Unknown requester", 401)

    if not fleet_name:
        raise_error("No fleet name")

    with DBSession() as dbsession:

        all_ongoing_trips_fleet = dbsession.get_all_ongoing_trips_fleet(fleet_name)
        if len(all_ongoing_trips_fleet):
            raise_error("Cancel all the ongoing trips before deleting the fleet")

        fleet: Fleet = dbsession.get_fleet(fleet_name)
        if not fleet:
            raise_error("Bad detail invalid fleet name")

        all_fleet_sherpas = dbsession.get_all_sherpas_in_fleet(fleet_name)

        # close ws connection to make sure new map files are downloaded by sherpa on reconnect
        for sherpa in all_fleet_sherpas:
            delete_sherpa(dbsession, sherpa.name)

        all_fleet_stations = dbsession.get_all_stations_in_fleet(fleet_name)
        for station in all_fleet_stations:
            delete_station(dbsession, station.name)

        map_id = fleet.map_id
        dbsession.session.delete(fleet)

        delete_map(dbsession, map_id)
        fu.delete_exclusion_zones(dbsession, fleet_name)

    return response


@router.get("/delete/sherpa/{sherpa_name}")
async def delete_sherpa_endoint(
    sherpa_name=Union[str, None],
    username=Depends(get_user_from_header),
):
    response = {}

    if not username:
        raise_error("Unknown requester", 401)

    if not sherpa_name:
        raise_error("No sherpa_name")

    with DBSession() as dbsession:
        delete_sherpa(dbsession, sherpa_name)

    return response
