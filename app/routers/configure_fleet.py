import os
import time
import logging
import glob
from fastapi import APIRouter, Depends, Form, File, HTTPException, UploadFile, status
from fastapi.encoders import jsonable_encoder
import shutil
import json
import hashlib
import aioredis
import zipfile
from rq.command import send_shutdown_command

# ati code imports
from utils import fleet_utils as fu
from models.db_session import DBSession
import models.fleet_models as fm
import models.request_models as rqm
import app.routers.dependencies as dpd
from utils.comms import close_websocket_for_sherpa
import utils.log_utils as lu
import core.common as ccm


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
    response = {}
    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    with DBSession(engine=ccm.engine) as dbsession:
        all_sherpas = dbsession.get_all_sherpas()
        [response.update({sherpa.name: jsonable_encoder(sherpa)}) for sherpa in all_sherpas]
        [
            response[sherpa.name].update({"fleet_name": sherpa.fleet.name})
            for sherpa in all_sherpas
        ]

    return response

@router.post("/switch_sherpa/{sherpa_name}")
async def switch_sherpa(
    add_edit_sherpa: rqm.AddEditSherpaReq,
    sherpa_name: str,
    user_name=Depends(dpd.get_user_from_header)
    ):

    response = {}

    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    with DBSession(engine=ccm.engine) as dbsession:
        sherpa_status: fm.SherpaStatus = dbsession.get_sherpa_status_with_none(sherpa_name)
        sherpa: fm.Sherpa = dbsession.get_sherpa(sherpa_name)
        fleet = dbsession.get_fleet(add_edit_sherpa.fleet_name)
        if not sherpa_status:
            dpd.raise_error(f"Sherpa {sherpa_name} not found")
        if add_edit_sherpa.api_key is None:
            hashed_api_key = sherpa.hashed_api_key
        else:
            hashed_api_key = hashlib.sha256(add_edit_sherpa.api_key.encode("utf-8")).hexdigest()

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
        try:
            fu.SherpaUtils.delete_sherpa(dbsession, sherpa_name)
            all_sherpa_names = dbsession.get_all_sherpa_names()
            async with aioredis.Redis.from_url(os.getenv("FM_REDIS_URI")) as aredis_conn:
                await fu.update_fleet_conf_in_redis(dbsession, aredis_conn)

                queues_to_delete = [
                    f"{sherpa_name}_update_handler",
                    f"{sherpa_name}_trip_update_handler",
                ]
                for q_name in queues_to_delete:
                    send_shutdown_command(aredis_conn, q_name)

            fu.SherpaUtils.add_edit_sherpa(
                dbsession,
                sherpa_name,
                hwid=add_edit_sherpa.hwid,
                api_key=hashed_api_key,
                fleet_id=fleet.id,
                sherpa_type=add_edit_sherpa.sherpa_type,
                is_add=add_edit_sherpa.is_add,
            )
            import utils.rq_utils as rqu
            from multiprocessing import Process


            all_sherpa_names.append(sherpa_name)
            lu.set_log_config_dict(all_sherpa_names)

            async with aioredis.Redis.from_url(os.getenv("FM_REDIS_URI")) as aredis_conn:
                await fu.update_fleet_conf_in_redis(dbsession, aredis_conn)

            new_qs = [f"{sherpa_name}_update_handler", f"{sherpa_name}_trip_update_handler"]
            for new_q in new_qs:
                rqu.Queues.add_queue(new_q)
                process = Process(target=rqu.start_worker, args=(new_q,))
                process.start()

        except Exception as e:
            dpd.relay_error_details(e)

    return response


@router.post("/add_edit_sherpa/{sherpa_name}")
async def add_edit_sherpa(
    add_edit_sherpa: rqm.AddEditSherpaReq,
    sherpa_name: str,
    user_name=Depends(dpd.get_user_from_header),
):

    response = {}
    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    with DBSession(engine=ccm.engine) as dbsession:
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
                sherpa_type=add_edit_sherpa.sherpa_type
            )
        except Exception as e:
            dpd.relay_error_details(e)

        if sherpa_name not in all_sherpa_names:
            import utils.rq_utils as rqu
            from multiprocessing import Process

            all_sherpa_names.append(sherpa_name)
            lu.set_log_config_dict(all_sherpa_names)

            async with aioredis.Redis.from_url(os.getenv("FM_REDIS_URI")) as aredis_conn:
                await fu.update_fleet_conf_in_redis(dbsession, aredis_conn)

            new_qs = [f"{sherpa_name}_update_handler", f"{sherpa_name}_trip_update_handler"]
            for new_q in new_qs:
                rqu.Queues.add_queue(new_q)
                process = Process(target=rqu.start_worker, args=(new_q,))
                process.start()

    return response


@router.get("/delete_sherpa/{sherpa_name}")
async def delete_sherpa(
    sherpa_name: str,
    user_name=Depends(dpd.get_user_from_header),
):
    response = {}

    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    with DBSession(engine=ccm.engine) as dbsession:
        sherpa_status: fm.SherpaStatus = dbsession.get_sherpa_status_with_none(sherpa_name)
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
        try:
            fu.SherpaUtils.delete_sherpa(dbsession, sherpa_name)
        except Exception as e:
            dpd.relay_error_details(e)

    async with aioredis.Redis.from_url(os.getenv("FM_REDIS_URI")) as aredis_conn:
        await fu.update_fleet_conf_in_redis(dbsession, aredis_conn)

        queues_to_delete = [
            f"{sherpa_name}_update_handler",
            f"{sherpa_name}_trip_update_handler",
        ]
        for q_name in queues_to_delete:
            send_shutdown_command(aredis_conn, q_name)

    return response


@router.get("/all_fleet_info")
async def get_all_fleet_info(user_name=Depends(dpd.get_user_from_header)):

    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    response = {}
    with DBSession(engine=ccm.engine) as dbsession:
        all_fleets = dbsession.get_all_fleets()
        [response.update({fleet.name: jsonable_encoder(fleet)}) for fleet in all_fleets]
    return response


@router.get("/get_all_available_maps/{fleet_name}")
async def get_all_available_maps(
    fleet_name: str, user_name=Depends(dpd.get_user_from_header)
):
    response = []
    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    with DBSession(engine=ccm.engine) as dbsession:
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
    fleet_name: str,
    site: str = Form(...),
    location: str = Form(...),
    customer: str = Form(...),
    map_name: str = Form(...),
    map_file: UploadFile = File(...),
    user_name=Depends(dpd.get_user_from_header),
):

    response = {}
    add_fleet_req = rqm.AddFleetReq(
        site=site,
        location=location,
        customer=customer,
        map_name=map_name,
    )

    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    if map_file:
        dir_to_save = os.getenv("FM_STATIC_DIR")
        os.makedirs(dir_to_save, exist_ok=True)
        file_path = os.path.join(dir_to_save, map_file.filename)
        try:
            with open(file_path, "wb") as f:
                f.write(await map_file.read())
            logging.getLogger("uvicorn").info(f"Uploaded file: {file_path} successfully")
            
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                zip_ref.extractall(os.getenv("FM_STATIC_DIR"))
        except Exception as e:
            dpd.raise_error(f"Couldn't upload file: {file_path}, exception: {e}")

    with DBSession(engine=ccm.engine) as dbsession:
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

        except Exception as e:
            dpd.relay_error_details(e)

        if new_fleet:
            async with aioredis.Redis.from_url(os.getenv("FM_REDIS_URI")) as aredis_conn:
                await fu.update_fleet_conf_in_redis(dbsession, aredis_conn)
                await aredis_conn.set("add_router_for", fleet_name)

    return response


@router.get("/delete_fleet/{fleet_name}")
async def delete_fleet(
    fleet_name: str,
    user_name=Depends(dpd.get_user_from_header),
):
    response = {}
    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    try:
        with DBSession(engine=ccm.engine) as dbsession:
            fleet: fm.Fleet = dbsession.get_fleet(fleet_name)
            if not fleet:
                raise Exception("Bad detail invalid fleet name")

            all_ongoing_trips_fleet = dbsession.get_all_ongoing_trips_fleet(fleet_name)
            if len(all_ongoing_trips_fleet):
                raise Exception("Cancel all the ongoing trips before deleting the fleet")

            all_fleet_sherpas = dbsession.get_all_sherpas_in_fleet(fleet_name)

            # close ws connection to make sure new map files are downloaded by sherpa on reconnect
            for sherpa in all_fleet_sherpas:
                close_websocket_for_sherpa(sherpa.name)
                if sherpa.status.trip_id is not None:
                    trip = dbsession.get_trip(sherpa.status.trip_id)
                    raise Exception(
                        f"delete the ongoing trip with booking_id: {trip.booking_id} and disable {sherpa.name} for trips to delete the sherpa and fleet"
                    )

                if sherpa.status.inducted:
                    raise Exception(
                        f"disable {sherpa.name} for trips to delete the sherpa and fleet"
                    )

                fu.SherpaUtils.delete_sherpa(dbsession, sherpa.name)

            fu.FleetUtils.delete_fleet(dbsession, fleet_name)

            async with aioredis.Redis.from_url(os.getenv("FM_REDIS_URI")) as aredis_conn:
                await fu.update_fleet_conf_in_redis(dbsession, aredis_conn)

    except Exception as e:
        dpd.relay_error_details(e)

    return response


@router.post("/update_map")
async def update_map(
    update_map_req: rqm.UpdateMapReq,
    user_name=Depends(dpd.get_user_from_header),
):
    response = {}

    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    with DBSession(engine=ccm.engine) as dbsession:
        fleet_name = update_map_req.fleet_name

        dpd.get_number_of_request(times=1, seconds=120, fleet_name=fleet_name)

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
            fu.ExclusionZoneUtils.delete_exclusion_zones(
                dbsession, fleet_name, update_map=True
            )
            fu.ExclusionZoneUtils.add_exclusion_zones(dbsession, fleet_name)
            fu.ExclusionZoneUtils.add_linked_gates(dbsession, fleet_name)

            all_fleet_sherpas = dbsession.get_all_sherpas_in_fleet(fleet_name)
            # close ws connection to make sure new map files are downloaded by sherpa on reconnect
            for sherpa in all_fleet_sherpas:
                close_websocket_for_sherpa(sherpa.name)

        except Exception as e:
            dpd.relay_error_details(e)

        async with aioredis.Redis.from_url(os.getenv("FM_REDIS_URI")) as aredis_conn:
            await fu.update_fleet_conf_in_redis(dbsession, aredis_conn)
            await aredis_conn.set("update_router_for", fleet_name)

    return response
