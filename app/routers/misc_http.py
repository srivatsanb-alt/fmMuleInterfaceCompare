from app.routers.dependencies import (
    get_user_from_header,
    raise_error,
)
from models.request_models import MasterDataInfo, RoutePreview
from models.fleet_models import SherpaEvent, Sherpa, SherpaStatus
from utils.util import get_table_as_dict, get_all_map_names
from fastapi import APIRouter, Depends
from models.db_session import DBSession
import toml
import os
import json
import secrets
from core.config import Config
from models.request_models import FleetConfigUpdate
from models.config_models import BasicConfig, FrontendUser, FleetSherpa

router = APIRouter(responses={404: {"description": "Not found"}}, prefix="/api/v1")


@router.get("/site_info")
async def site_info(user_name=Depends(get_user_from_header)):

    if not user_name:
        raise_error("Sherpa not yet connected to the fleet manager")

    config = Config.read_config()
    fleet_names = config["fleet"]["fleet_names"]
    site = config["fleet"]["site"]
    location = config["fleet"]["location"]
    customer = config["fleet"]["customer"]
    timezone = os.environ["PGTZ"]
    fm_tag = os.environ["FM_TAG"]

    response = {
        "fleet_names": fleet_names,
        "timezone": timezone,
        "customer": customer,
        "site": site,
        "location": location,
        "software_version": fm_tag,
    }

    return response


@router.post("/master_data/fleet")
async def master_data(
    master_data_info: MasterDataInfo, user_name=Depends(get_user_from_header)
):

    if not user_name:
        raise_error("Sherpa not yet connected to the fleet manager")

    with DBSession() as session:
        fleet_names = Config.get_all_fleets()

        if master_data_info.fleet_name not in fleet_names:
            raise_error("Unknown fleet")

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


@router.get("/sherpa_summary/{sherpa_name}/{viewable}")
async def sherpa_summary(
    sherpa_name: str, viewable: int, user_name=Depends(get_user_from_header)
):
    response = {}
    if not user_name:
        raise_error("Unknown requester")

    with DBSession() as session:
        recent_events = session.get_sherpa_events(sherpa_name)
        result = []
        for recent_event in recent_events:
            temp = get_table_as_dict(SherpaEvent, recent_event)
            result.append(temp)

        response.update({"recent_events": {"events": result}})
        sherpa: Sherpa = session.get_sherpa(sherpa_name)
        response.update({"sherpa": get_table_as_dict(Sherpa, sherpa)})
        response.update({"fleet_name": sherpa.fleet.name})
        sherpa_status: SherpaStatus = session.get_sherpa_status(sherpa_name)
        response.update({"sherpa_status": get_table_as_dict(SherpaStatus, sherpa_status)})

    return response


@router.post("/trips/get_route_wps")
async def get_route_wps(
    route_preview_req: RoutePreview,
    user_name=Depends(get_user_from_header),
):
    if not user_name:
        raise_error("Unknown requester")

    with DBSession() as session:
        stations_poses = []
        fleet_name = route_preview_req.fleet_name
        for station_name in route_preview_req.route:
            station = session.get_station(station_name)
            stations_poses.append(station.pose)

    return {}


@router.get("/get_fleet_config")
async def get_fleet_config(
    user_name=Depends(get_user_from_header),
):
    if not user_name:
        raise_error("Unknown requester")

    fleet_config_path = os.path.join(os.getenv("FM_CONFIG_DIR"), "fleet_config.toml")
    fleet_config = toml.load(fleet_config_path)

    response = BasicConfig.from_dict(fleet_config["fleet"])
    # response_json = {"basic_config": json.loads(response.to_json())}

    fleets = {}
    for fleet_name in response.fleet_names:
        fleet_map_mapping = fleet_config["fleet"].get("fleet_map_mapping")
        map_name = fleet_name
        fleets[fleet_name] = map_name
    if fleet_map_mapping:
        pass
    else:
        response.fleet_map_mapping = fleets

    map_names = fleet_config["fleet"].get("map_names")
    if map_names:
        pass
    else:
        response.map_names = get_all_map_names()

    response_json = {"fleet": json.loads(response.to_json())}

    # fleets = []
    # for fleet_name in response.fleet_names:
    #    fleet_map_mapping = fleet_config["fleet"].get("fleet_map_mapping")
    #    map_name = fleet_name

    #    if fleet_map_mapping:
    #        map_name = fleet_map_mapping.get(fleet_name)

    #    fleets.append(Fleet(name=fleet_name, map_name=map_name))

    # FrontendUsers
    frontendusers = []
    for user, user_details in fleet_config["frontenduser"].items():
        frontendusers.append(
            FrontendUser(
                name=user,
                role=user_details.get("role", "default"),
                hashed_password=user_details.get("hashed_password"),
            )
        )

    # fleet_sherpas
    fleetsherpas = []
    for sherpa_name, sherpa_details in fleet_config["fleet_sherpas"].items():
        fleetsherpas.append(
            FleetSherpa(
                name=sherpa_name,
                hwid=sherpa_details["hwid"],
                api_key=sherpa_details["api_key"],
                fleet_name=sherpa_details["fleet_name"],
            )
        )

    # optimal_dispatch = []

    response_json.update({"optimal_dispatch": fleet_config["optimal_dispatch"]})
    # response_json.update({"fleets": fleets})
    response_json.update({"frontendusers": frontendusers})
    response_json.update({"fleet_sherpas": fleetsherpas})

    return response_json


@router.post("/update_fleet_config")
async def update_fleet_config(
    fleet_config_update: FleetConfigUpdate, user_name=Depends(get_user_from_header)
):
    if not user_name:
        raise_error("Unknown requester")

    fleet_config_path = os.path.join(os.getenv("FM_CONFIG_DIR"), "fleet_config.toml")
    previous_fleet_config_path = os.path.join(
        os.getenv("FM_CONFIG_DIR"), "previous_fleet_config.toml"
    )
    previous_fleet_config = toml.load(fleet_config_path)
    with open(previous_fleet_config_path, "w") as f:
        f.write(toml.dumps(previous_fleet_config))

    new_config = {}

    new_fleet = json.loads(fleet_config_update.fleet.to_json())
    new_optimal_dispatch = json.loads(fleet_config_update.optimal_dispatch.to_json())
    new_config.update({"fleet": new_fleet})
    new_config.update({"optimal_dispatch": new_optimal_dispatch})

    # new_config.update({"fleet": fleet_config_update.dict()["fleet"]})
    # new_config.update({"optimal_dispatch": fleet_config_update.dict()["optimal_dispatch"]})

    new_config["fleet_sherpas"] = {}
    for fleet_sherpa in fleet_config_update.fleet_sherpas:
        sherpa_config = json.loads(fleet_sherpa.to_json())
        if sherpa_config["api_key"] is None:
            sherpa_config["api_key"] = (
                secrets.token_urlsafe(32) + "_" + sherpa_config["hwid"]
            )

        del sherpa_config["name"]
        new_config["fleet_sherpas"].update({fleet_sherpa.name: sherpa_config})

    new_config["frontenduser"] = {}
    for frontenduser in fleet_config_update.frontendusers:
        user_config = json.loads(frontenduser.to_json())
        del user_config["name"]
        new_config["frontenduser"].update({frontenduser.name: user_config})

    for fleet_name, map_name in fleet_config_update.fleet.fleet_map_mapping.items():
        if fleet_name != map_name:
            try:
                fleet_static_dir = os.getenv("FM_MAP_DIR")
                os.system(f"cd {fleet_static_dir} ; ln -s {map_name} {fleet_name}")
            except:
                pass

    with open(fleet_config_path, "w") as f:
        f.write(toml.dumps(new_config))
    # return new_config
