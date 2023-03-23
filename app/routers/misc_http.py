import json
import os
import time
from fastapi import APIRouter, Depends
import aioredis

# ati code imports
from utils.util import get_table_as_dict
import models.request_models as rqm
import models.fleet_models as fm
import models.misc_models as mm
from models.db_session import DBSession
import app.routers.dependencies as dpd
from utils.util import generate_random_job_id


router = APIRouter(responses={404: {"description": "Not found"}}, prefix="/api/v1")


@router.get("/site_info")
async def site_info(user_name=Depends(dpd.get_user_from_header)):

    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    with DBSession() as session:
        fleet_names = session.get_all_fleet_names()

    timezone = os.environ["PGTZ"]
    fm_tag = os.environ["FM_TAG"]

    response = {
        "fleet_names": fleet_names,
        "timezone": timezone,
        "software_version": fm_tag,
    }

    return response


# returns info about all the sherpas, stations and their corresponding status(initialized, inducted, disabled, idle, etc.).


@router.post("/master_data/fleet")
async def master_data(
    master_data_info: rqm.MasterDataInfo, user_name=Depends(dpd.get_user_from_header)
):

    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    with DBSession() as session:
        fleet_names = session.get_all_fleet_names()

        if master_data_info.fleet_name not in fleet_names:
            dpd.raise_error("Unknown fleet")

        all_sherpas = session.get_all_sherpas_in_fleet(master_data_info.fleet_name)
        all_stations = session.get_all_stations_in_fleet(master_data_info.fleet_name)

        response = {}
        sherpa_list = []
        station_list = []

        if all_sherpas:
            sherpa_list = [sherpa.name for sherpa in all_sherpas]

        if all_stations:
            station_list = [station.name for station in all_stations]

        response.update({"sherpa_list": sherpa_list})
        response.update({"station_list": station_list})

        sample_sherpa_status = {}
        all_sherpa_status = session.get_all_sherpa_status()
        if len(all_sherpa_status) > 0:
            sample_sherpa_status.update(
                {all_sherpa_status[0].sherpa_name: all_sherpa_status[0].__dict__}
            )
            sample_sherpa_status[all_sherpa_status[0].sherpa_name].update(
                all_sherpa_status[0].sherpa.__dict__
            )
            response.update({"sample_sherpa_status": sample_sherpa_status})

        sample_station_status = {}
        all_station_status = session.get_all_station_status()
        if len(all_station_status) > 0:
            sample_station_status.update(
                {all_station_status[0].station_name: all_station_status[0].__dict__}
            )

            sample_station_status[all_station_status[0].station_name].update(
                all_station_status[0].station.__dict__
            )
            response.update({"sample_station_status": sample_station_status})

    return response


# returns sherpa, the fleet it belongs to and its status.


@router.get("/sherpa_summary/{sherpa_name}/{viewable}")
async def sherpa_summary(
    sherpa_name: str, viewable: int, user_name=Depends(dpd.get_user_from_header)
):
    response = {}
    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    with DBSession() as session:
        recent_events = session.get_sherpa_events(sherpa_name)
        result = []
        for recent_event in recent_events:
            temp = get_table_as_dict(fm.SherpaEvent, recent_event)
            result.append(temp)

        response.update({"recent_events": {"events": result}})
        sherpa: fm.Sherpa = session.get_sherpa(sherpa_name)
        response.update({"sherpa": get_table_as_dict(fm.Sherpa, sherpa)})
        response.update({"fleet_name": sherpa.fleet.name})
        sherpa_status: fm.SherpaStatus = session.get_sherpa_status(sherpa_name)
        response.update(
            {"sherpa_status": get_table_as_dict(fm.SherpaStatus, sherpa_status)}
        )

    return response


# gets the route(sequence of stations) for a trip


@router.post("/trips/get_route_wps")
async def get_route_wps(
    route_preview_req: rqm.RoutePreview,
    user_name=Depends(dpd.get_user_from_header),
):
    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    redis_conn = aioredis.Redis.from_url(
        os.getenv("FM_REDIS_URI"), max_connections=10, decode_responses=True
    )

    response = {}

    with DBSession() as session:
        stations_poses = []
        fleet_name = session.get_fleet_name_from_route(route_preview_req.route)
        for station_name in route_preview_req.route:
            station = session.get_station(station_name)
            stations_poses.append(station.pose)
        job_id = generate_random_job_id()
        control_router_wps_job = [stations_poses, fleet_name, job_id]
        await redis_conn.set(
            f"control_router_wps_job_{job_id}", json.dumps(control_router_wps_job)
        )

        while not await redis_conn.get(f"result_wps_job_{job_id}"):
            time.sleep(0.005)

        wps_list = json.loads(await redis_conn.get(f"result_wps_job_{job_id}"))

        if not len(wps_list):
            dpd.raise_error("Cannot find route")

        response.update({"wps_list": wps_list})
        await redis_conn.delete(f"result_wps_job_{job_id}")

    return response


@router.post("/trips/get_sherpa_live_route")
async def get_sherpa_live_route(
    live_route_req: rqm.LiveRoute,
    user_name=Depends(dpd.get_user_from_header),
):

    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    response = {}

    with DBSession() as session:
        ongoing_trip = session.get_enroute_trip(live_route_req.sherpa_name)

        if not ongoing_trip:
            dpd.raise_error(f"No ongoing trip for {live_route_req.sherpa_name}")

        ongoing_route = ongoing_trip.route
        wps_req = rqm.RoutePreview(route=ongoing_route)
        response = await get_route_wps(wps_req, user_name)

    return response


@router.get("/sherpa_build_info/{sherpa_name}")
async def sherpa_build_info(sherpa_name: str, user_name=Depends(dpd.get_user_from_header)):
    response = {}
    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    with DBSession() as dbsession:
        sherpa_status = dbsession.get_sherpa_status(sherpa_name)

        if not sherpa_status:
            dpd.raise_error("Invalid sherpa name")

        if sherpa_status.other_info is not None:
            response.update(
                {
                    "last_software_update": sherpa_status.other_info.get(
                        "last_software_update"
                    )
                }
            )
            response.update({"sw_date": sherpa_status.other_info.get("sw_date")})
            response.update({"sw_tag": sherpa_status.other_info.get("sw_tag")})
            response.update({"sw_id": sherpa_status.other_info.get("sw_id")})

    return response


# alerts the FM with messages from Sherpa
@router.get("/create_generic_alerts/{alert_description}")
async def create_generic_alerts(
    alert_description: str, user_name=Depends(dpd.get_user_from_header)
):
    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    with DBSession() as dbsession:
        dbsession.add_notification(
            [],
            alert_description,
            mm.NotificationLevels.action_request,
            mm.NotificationModules.generic,
        )
