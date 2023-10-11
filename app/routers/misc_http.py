import json
import os
import asyncio
from fastapi.encoders import jsonable_encoder
import aioredis
import subprocess
import redis
from fastapi import APIRouter, Depends
from sqlalchemy.orm.attributes import flag_modified

# ati code imports
from models.mongo_client import FMMongo
import models.visa_models as vm
import models.request_models as rqm
import models.fleet_models as fm
import models.misc_models as mm
from models.db_session import DBSession
import app.routers.dependencies as dpd
import utils.util as utils_util


router = APIRouter(
    responses={404: {"description": "Not found"}}, tags=["misc"], prefix="/api/v1"
)


@router.get("/site_info")
async def site_info(user_name=Depends(dpd.get_user_from_header)):
    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    with DBSession() as dbsession:
        fleet_names = dbsession.get_all_fleet_names()
        software_compatability = dbsession.get_compatability_info()
        compatible_sherpa_versions = software_compatability.info.get("sherpa_versions", [])

    timezone = os.environ["PGTZ"]
    fm_tag = os.environ["FM_TAG"]

    with FMMongo() as fm_mongo:
        simulator_config = fm_mongo.get_document_from_fm_config("simulator")

    response = {
        "fleet_names": fleet_names,
        "timezone": timezone,
        "software_version": fm_tag,
        "compatible_sherpa_versions": compatible_sherpa_versions,
        "simulator": simulator_config["simulate"],
    }

    return response


@router.get("/get_trip_metadata")
async def get_trip_metadata(user_name=Depends(dpd.get_user_from_header)):

    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    with FMMongo() as fm_mongo:
        trip_metadata = fm_mongo.get_document_from_fm_config("trip_metadata")

    return trip_metadata


# returns info about all the sherpas, stations and their corresponding status(initialized, inducted, disabled, idle, etc.).


@router.post("/master_data/fleet")
async def master_data(
    master_data_info: rqm.MasterDataInfo, user_name=Depends(dpd.get_user_from_header)
):
    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    with DBSession() as dbsession:
        fleet_names = dbsession.get_all_fleet_names()

        if master_data_info.fleet_name not in fleet_names:
            dpd.raise_error("Unknown fleet")

        all_sherpas = dbsession.get_all_sherpas_in_fleet(master_data_info.fleet_name)
        all_stations = dbsession.get_all_stations_in_fleet(master_data_info.fleet_name)

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
        all_sherpa_status = dbsession.get_all_sherpa_status()
        if len(all_sherpa_status) > 0:
            sample_sherpa_status.update(
                {all_sherpa_status[0].sherpa_name: all_sherpa_status[0].__dict__}
            )
            sample_sherpa_status[all_sherpa_status[0].sherpa_name].update(
                all_sherpa_status[0].sherpa.__dict__
            )
            response.update({"sample_sherpa_status": sample_sherpa_status})

        sample_station_status = {}
        all_station_status = dbsession.get_all_station_status()
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

    with DBSession() as dbsession:
        recent_events = dbsession.get_sherpa_events(sherpa_name)
        result = []
        for recent_event in recent_events:
            temp = utils_util.get_table_as_dict(fm.SherpaEvent, recent_event)
            result.append(temp)

        response.update({"recent_events": {"events": result}})
        sherpa: fm.Sherpa = dbsession.get_sherpa(sherpa_name)
        response.update({"sherpa": utils_util.get_table_as_dict(fm.Sherpa, sherpa)})
        response.update({"fleet_name": sherpa.fleet.name})
        sherpa_status: fm.SherpaStatus = dbsession.get_sherpa_status(sherpa_name)
        response.update(
            {"sherpa_status": utils_util.get_table_as_dict(fm.SherpaStatus, sherpa_status)}
        )

    return response


# gets the route(sequence of stations) for a trip
@router.post("/update_sherpa_metadata")
async def update_sherpa_metadata(
    update_sherpa_metadata_req: rqm.UpdateSherpaMetaDataReq,
    user_name=Depends(dpd.get_user_from_header),
):
    response = {}
    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    with DBSession() as dbsession:
        sherpa_name = update_sherpa_metadata_req.sherpa_name
        sherpa_metadata = dbsession.get_sherpa_metadata(sherpa_name)

        if sherpa_metadata is None:
            dpd.raise_error(f"sherpa metadata for {sherpa_name} not found")

        sherpa_metadata.info.update(update_sherpa_metadata_req.info)
        flag_modified(sherpa_metadata, "info")

    return response


@router.get("/sherpa_metadata/{sherpa_name}")
async def get_sherpa_metadata(
    sherpa_name: str, user_name=Depends(dpd.get_user_from_header)
):
    response = {}
    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    with DBSession() as dbsession:
        sherpa_metadata = dbsession.get_sherpa_metadata(sherpa_name)
        if not sherpa_metadata:
            dpd.raise_error(f"sherpa metadata for {sherpa_name} not found")

        response.update({"info": sherpa_metadata.info})

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

    with DBSession() as dbsession:
        stations_poses = []
        fleet_name = dbsession.get_fleet_name_from_route(route_preview_req.route)
        for station_name in route_preview_req.route:
            station = dbsession.get_station(station_name)
            stations_poses.append(station.pose)
        job_id = utils_util.generate_random_job_id()
        control_router_wps_job = [stations_poses, fleet_name, job_id]
        await redis_conn.setex(
            f"control_router_wps_job_{job_id}",
            5 * int((await redis_conn.get("default_job_timeout_ms"))),
            json.dumps(control_router_wps_job),
        )

        while not await redis_conn.get(f"result_wps_job_{job_id}"):
            await asyncio.sleep(0.005)

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

    with DBSession() as dbsession:
        ongoing_trip = dbsession.get_enroute_trip(live_route_req.sherpa_name)

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
        utils_util.maybe_add_notification(
            dbsession,
            dbsession.get_customer_names(),
            alert_description,
            mm.NotificationLevels.alert,
            mm.NotificationModules.generic,
        )


@router.post("/get_fm_incidents")
async def get_fm_incidents(
    get_fm_incident: rqm.GetFMIncidents, user_name=Depends(dpd.get_user_from_header)
):
    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    response = {}
    with DBSession() as dbsession:
        fm_incidents = dbsession.get_recent_fm_incident(
            get_fm_incident.sherpa_name, n=get_fm_incident.num_of_incidents
        )

        if fm_incidents is None:
            return response

        for fm_incident in fm_incidents:
            incident_id = fm_incident.incident_id
            response[incident_id] = {}
            response[incident_id].update({"code": fm_incident.code})
            response[incident_id].update({"message": fm_incident.message})
            response[incident_id].update({"description": fm_incident.display_message})
            response[incident_id].update({"how_to_recover": fm_incident.recovery_message})
            response[incident_id].update(
                {"reported_at": utils_util.dt_to_str(fm_incident.created_at)}
            )
            response[incident_id].update({"module": fm_incident.module})
            response[incident_id].update({"other_info": fm_incident.other_info})

    return response


@router.get("/get_visa_assignments")
async def get_visa_assignments(user_name=Depends(dpd.get_user_from_header)):
    response = []
    if not user_name:
        dpd.raise_error("Unknown requester", 401)
    with DBSession() as dbsession:
        zone_ids = dbsession.session.query(vm.ExclusionZone.zone_id).all()
        response = jsonable_encoder(zone_ids)
        for item in response:
            visa_assignments = dbsession.get_all_visa_assignments_as_dict(item["zone_id"])
            item["resident_sherpas"] = (
                visa_assignments["resident_sherpas"]
                if (visa_assignments["resident_sherpas"])
                else []
            )
            item["waiting_sherpas"] = (
                visa_assignments["waiting_sherpas"]
                if (visa_assignments["waiting_sherpas"])
                else []
            )
    return response


@router.post("/get_sherpa_oee/{sherpa_name}")
async def get_sherpa_oee(
    generic_time_req: rqm.GenericFromToTimeReq,
    sherpa_name: str,
    user_name=Depends(dpd.get_user_from_header),
):
    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    with DBSession() as dbsession:
        from_dt = utils_util.str_to_dt(generic_time_req.from_dt)
        to_dt = utils_util.str_to_dt(generic_time_req.to_dt)

        from_dt_start = from_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        to_dt_end = to_dt.replace(hour=23, minute=59, second=59, microsecond=0)

        sherpa_oee_data = (
            dbsession.session.query(mm.SherpaOEE)
            .filter(mm.SherpaOEE.sherpa_name == sherpa_name)
            .filter(mm.SherpaOEE.dt >= from_dt_start)
            .filter(mm.SherpaOEE.dt <= to_dt_end)
            .all()
        )
        response = {}
        response["mode_split_up"] = {}
        for sherpa_oee in sherpa_oee_data:
            for key, val in sherpa_oee.mode_split_up.items():
                if key in response["mode_split_up"]:
                    response["mode_split_up"][key] += round(val, 2)
                else:
                    response["mode_split_up"][key] = round(val, 2)

        total_time = sum(response["mode_split_up"].values())
        for key, val in response["mode_split_up"].items():
            temp = response["mode_split_up"][key] / total_time
            temp = round(temp * 100, 2)
            response["mode_split_up"][key] = temp

        response["uptime"] = 0
        if response["mode_split_up"].get("fleet", 0):
            fleet_time = response["mode_split_up"].get("fleet", 0)
            error_time = response["mode_split_up"].get("error", 0)
            oee = (fleet_time * 100) / (fleet_time + error_time)
            response["uptime"] = round(oee, 2)

        response[
            "msg"
        ] = f"Data considered from {utils_util.dt_to_str(from_dt_start)} to {utils_util.dt_to_str(to_dt_end)}"

        # #response["utilisation"] = 0
        # # percentage of time spent in fleet mode
        # if response["mode_split_up"].get("fleet", 0):
        #     oee = (response["mode_split_up"].get("fleet", 0) * 100) / sum(
        #         response["mode_split_up"].values()
        #     )
        #     response["OEE"] = round(oee, 2)
        #
        #     # time in seconds spent doing trips
        #     trip_time = dbsession.get_sherpa_trip_time_with_timestamp(
        #         sherpa_name, from_dt_start, to_dt_end
        #     )
        #     if trip_time is not None:
        #         trip_time = round(trip_time, 2)
        #         response["utilisation"] = (trip_time * 100) / sum(
        #             response["mode_split_up"].values()
        #         )

    return response


@router.get("/fm_health_stats")
async def fm_health_stats(
    user_name=Depends(dpd.get_user_from_header),
):
    response = {}
    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    # rq perf
    column_names, rq_perf_data = utils_util.rq_perf()
    all_rq_perf = []
    # queue wise data
    valid_rq_perf_cols_names = ["worker_queues", "num_jobs"]
    for data in rq_perf_data:
        rq_perf_dict = {}
        for col, val in zip(column_names, data):
            if col in valid_rq_perf_cols_names:
                rq_perf_dict[col] = val
        all_rq_perf.append(rq_perf_dict)

    # sys perf
    column_names, sys_perf_data = utils_util.sys_perf()
    valid_sys_perf_cols_names = [
        "cpu_count",
        "load_avg_1",
        "mem_used_gb",
        "mem_available_gb",
        "swap_used_gb",
    ]

    sys_perf_dict = {}
    for col, val in zip(column_names, sys_perf_data):
        if col in valid_sys_perf_cols_names:
            sys_perf_dict[col] = val

    response["rq_perf"] = all_rq_perf
    response["sys_perf"] = sys_perf_dict

    # GET DISK USAGE
    total_disk_usage = []
    static_disk_usage = subprocess.check_output("du /app/static/ -d 1 -h ", shell=True)
    if static_disk_usage is not None:
        static_disk_usage = static_disk_usage.decode()
        static_disk_usage = static_disk_usage.split("\n")
        for item in static_disk_usage:
            total_disk_usage.append(item.split("\t"))

    logs_disk_usage = subprocess.check_output("du /app/logs/ -d 1 -h ", shell=True)
    if logs_disk_usage is not None:
        logs_disk_usage = logs_disk_usage.decode()
        logs_disk_usage = logs_disk_usage.split("\n")

        for item in logs_disk_usage:
            total_disk_usage.append(item.split("\t"))

        response["disk_usage"] = total_disk_usage

    # get current folder
    redis_conn = redis.from_url(os.getenv("FM_REDIS_URI"))
    fm_backup_path = os.path.join(os.getenv("FM_STATIC_DIR"), "data_backup")
    current_data = redis_conn.get("current_data_folder").decode()
    response["current_data_folder"] = os.path.join(fm_backup_path, current_data)

    return response


@router.get("/get_downloads")
async def get_downloads(
    user_name=Depends(dpd.get_user_from_header),
):
    reponse = {}
    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    reponse["downloads"] = os.listdir(os.getenv("FM_DOWNLOAD_DIR"))
    reponse["url_prefix"] = "/api/downloads"

    return reponse
