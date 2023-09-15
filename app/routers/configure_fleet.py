import os
import logging
import glob
from fastapi import APIRouter, Depends
import shutil

# ati code imports
from utils import fleet_utils as fu
from models.db_session import DBSession
import models.fleet_models as fm
import models.misc_models as mm
import models.request_models as rqm
import app.routers.dependencies as dpd
from utils.comms import close_websocket_for_sherpa
import utils.log_utils as lu

# manages the overall configuration of fleet by- deleting sherpa, fleet, map, station; update map.
# get log config
logging.config.dictConfig(lu.get_log_config_dict())
logger = logging.getLogger("configure_fleet")

router = APIRouter(
    prefix="/api/v1/configure_fleet",
    tags=["configure_fleet"],
    responses={404: {"description": "Not found"}},
)


@router.get("/all_sherpa_info")
async def get_all_sherpa_info(user_name=Depends(dpd.get_user_from_header)):

    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    response = {}
    with DBSession() as dbsession:
        all_sherpas = dbsession.get_all_sherpas()
        if all_sherpas:
            for sherpa in all_sherpas:
                response.update(
                    {
                        sherpa.name: {
                            "hwid": sherpa.hwid,
                            "api_key": sherpa.hashed_api_key,
                            "fleet_name": sherpa.fleet.name,
                        }
                    }
                )

    return response


@router.post("/add_edit_sherpa/{sherpa_name}")
async def add_edit_sherpa(
    add_edit_sherpa: rqm.AddEditSherpaReq,
    sherpa_name: str,
    user_name=Depends(dpd.get_user_from_header),
):

    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    with DBSession() as dbsession:
        all_sherpa_names = dbsession.get_all_sherpa_names()

        fleet = dbsession.get_fleet(add_edit_sherpa.fleet_name)
        if not fleet:
            dpd.raise_error("Unkown fleet")
        try:
            fu.SherpaUtils.add_edit_sherpa(
                dbsession,
                sherpa_name,
                hwid=add_edit_sherpa.hwid,
                api_key=add_edit_sherpa.api_key,
                fleet_id=fleet.id,
            )

            if sherpa_name not in all_sherpa_names:
                action_request = f"New sherpa {sherpa_name} has been added to {fleet.name}, please restart FM software using restart fleet manager button in the maintenance page"
                dbsession.add_notification(
                    [fleet.name],
                    action_request,
                    mm.NotificationLevels.alert,
                    mm.NotificationModules.generic,
                )

        except Exception as e:
            if isinstance(e, ValueError):
                dpd.raise_error(str(e))
            else:
                raise e

    return {}


@router.get("/delete_sherpa/{sherpa_name}")
async def delete_sherpa(
    sherpa_name: str,
    user_name=Depends(dpd.get_user_from_header),
):
    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    with DBSession() as dbsession:
        sherpa_status: fm.SherpaStatus = dbsession.get_sherpa_status(sherpa_name)
        if not sherpa_status:
            dpd.raise_error(f"Sherpa {sherpa_name} not found")

        if sherpa_status.trip_id:
            trip = dbsession.get_trip(sherpa_status.trip_id)
            dpd.raise_error(
                f"delete the ongoing trip with booking_id: {trip.booking_id} and disable {sherpa_status.sherpa_name} for trips to delete the sherpa"
            )

        if sherpa_status.inducted:
            dpd.raise_error(
                f"disable {sherpa_status.sherpa_name} for trips to delete the sherpa"
            )

        close_websocket_for_sherpa(sherpa_name)
        fu.SherpaUtils.delete_sherpa(dbsession, sherpa_name)

    return {}


@router.get("/all_fleet_info")
async def get_all_fleet_info(user_name=Depends(dpd.get_user_from_header)):

    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    response = {}
    with DBSession() as dbsession:
        all_fleets = dbsession.get_all_fleets()
        for fleet in all_fleets:
            response.update(
                {
                    fleet.name: {
                        "name": fleet.name,
                        "map_name": fleet.name,
                        "customer": fleet.customer,
                        "site": fleet.site,
                        "location": fleet.location,
                    }
                }
            )

    return response


@router.get("/get_all_available_maps/{fleet_name}")
async def get_all_available_maps(
    fleet_name: str, user_name=Depends(dpd.get_user_from_header)
):
    response = []
    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    with DBSession() as dbsession:
        all_fleets = dbsession.get_all_fleet_names()
        new_fleet = False if fleet_name in all_fleets else True
        if new_fleet:
            dpd.raise_error("Add the fleet to get_all_available_maps", 401)

        response.append("use current map")
        temp = os.path.join(os.getenv("FM_STATIC_DIR"), fleet_name, "all_maps", "*")
        for item in glob.glob(temp):
            if os.path.isdir(item):
                map_folder_name = item
                map_folder_name = item.rsplit("/")[-1]
                response.append(map_folder_name)

    return response


@router.post("/add_edit_fleet/{fleet_name}")
async def add_fleet(
    add_fleet_req: rqm.AddFleetReq,
    fleet_name: str,
    user_name=Depends(dpd.get_user_from_header),
):

    response = {}

    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    with DBSession() as dbsession:
        all_fleets = dbsession.get_all_fleet_names()
        new_fleet = False if fleet_name in all_fleets else True
        try:
            fu.FleetUtils.add_map(dbsession, fleet_name)
            fu.FleetUtils.add_fleet(
                dbsession,
                fleet_name,
                add_fleet_req.site,
                add_fleet_req.location,
                add_fleet_req.customer,
            )

            fleet: fm.Fleet = dbsession.get_fleet(fleet_name)
            fu.FleetUtils.update_stations_in_map(dbsession, fleet.name, fleet.id)
            fu.ExclusionZoneUtils.add_exclusion_zones(dbsession, fleet.name)
            fu.ExclusionZoneUtils.add_linked_gates(dbsession, fleet.name)

            if new_fleet:
                action_request = f"New fleet {fleet.name} has been added, please restart FM software using restart fleet manager button in the maintenance page"
                dbsession.add_notification(
                    [fleet.name],
                    action_request,
                    mm.NotificationLevels.action_request,
                    mm.NotificationModules.generic,
                )
        except Exception as e:
            if isinstance(e, ValueError):
                dpd.raise_error(str(e))
            else:
                raise e

    return response


@router.get("/delete_fleet/{fleet_name}")
async def delete_fleet(
    fleet_name: str,
    user_name=Depends(dpd.get_user_from_header),
):
    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    with DBSession() as dbsession:
        fleet: fm.Fleet = dbsession.get_fleet(fleet_name)
        if not fleet:
            dpd.raise_error("Bad detail invalid fleet name")

        all_ongoing_trips_fleet = dbsession.get_all_ongoing_trips_fleet(fleet_name)
        if len(all_ongoing_trips_fleet):
            dpd.raise_error("Cancel all the ongoing trips before deleting the fleet")

        all_fleet_sherpas = dbsession.get_all_sherpas_in_fleet(fleet_name)

        # close ws connection to make sure new map files are downloaded by sherpa on reconnect
        for sherpa in all_fleet_sherpas:
            close_websocket_for_sherpa(sherpa.name)
            if sherpa.status.trip_id is not None:
                trip = dbsession.get_trip(sherpa.status.trip_id)
                dpd.raise_error(
                    f"delete the ongoing trip with booking_id: {trip.booking_id} and disable {sherpa.name} for trips to delete the sherpa and fleet"
                )

            if sherpa.status.inducted:
                dpd.raise_error(
                    f"disable {sherpa.name} for trips to delete the sherpa and fleet"
                )

            fu.SherpaUtils.delete_sherpa(dbsession, sherpa.name)

        fu.FleetUtils.delete_fleet(dbsession, fleet_name)

    return {}


# deletes fleet from FM.


@router.post("/update_map")
async def update_map(
    update_map_req: rqm.UpdateMapReq,
    user_name=Depends(dpd.get_user_from_header),
):
    response = {}

    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    with DBSession() as dbsession:
        fleet_name = update_map_req.fleet_name

        if update_map_req.map_path != "use current map":
            new_map = os.path.join(
                os.getenv("FM_STATIC_DIR"), fleet_name, "all_maps", update_map_req.map_path
            )
            current_map = os.path.join(os.getenv("FM_STATIC_DIR"), fleet_name, "map")
            prev_map = os.path.join(os.getenv("FM_STATIC_DIR"), fleet_name, "prev_map")
            try:
                shutil.copytree(current_map, prev_map)
                shutil.rmtree(current_map)
                shutil.copytree(new_map, current_map)
            except Exception as e:
                shutil.copytree(prev_map, current_map)
                shutil.rmtree(prev_map)
                dpd.raise_error(str(e))

            shutil.rmtree(prev_map)

        fleet: fm.Fleet = dbsession.get_fleet(fleet_name)
        if not fleet:
            dpd.raise_error("Bad detail invalid fleet name")

        all_ongoing_trips_fleet = dbsession.get_all_ongoing_trips_fleet(fleet_name)
        if len(all_ongoing_trips_fleet):
            dpd.raise_error("Cancel all the ongoing trips before updating the map")

        try:
            fu.FleetUtils.add_map(dbsession, fleet_name)
            fu.FleetUtils.update_stations_in_map(dbsession, fleet_name, fleet.id)
            fu.ExclusionZoneUtils.delete_exclusion_zones(dbsession, fleet_name)
            fu.ExclusionZoneUtils.add_exclusion_zones(dbsession, fleet_name)
            fu.ExclusionZoneUtils.add_linked_gates(dbsession, fleet_name)

            all_fleet_sherpas = dbsession.get_all_sherpas_in_fleet(fleet_name)
            # close ws connection to make sure new map files are downloaded by sherpa on reconnect
            for sherpa in all_fleet_sherpas:
                close_websocket_for_sherpa(sherpa.name)

            restart_fm_notification = (
                f"Map files of fleet: {fleet_name} updated! Please restart fleet manager"
            )

            dbsession.add_notification(
                [fleet_name],
                restart_fm_notification,
                mm.NotificationLevels.alert,
                mm.NotificationModules.generic,
            )

        except Exception as e:
            if isinstance(e, ValueError):
                dpd.raise_error(str(e))
            else:
                raise e

    return response
