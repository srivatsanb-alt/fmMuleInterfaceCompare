from app.routers.dependencies import get_db_session, get_user_from_header
from models.request_models import MasterDataInfo, RoutePreview
from fastapi import APIRouter, Depends, HTTPException
from models.fleet_models import SherpaEvent, Sherpa, SherpaStatus
import utils.fleet_utils as fu
from utils.util import dt_to_str
from models.db_session import session
from typing import List
import pandas as pd
import os
from fastapi.responses import HTMLResponse

router = APIRouter(
    responses={404: {"description": "Not found"}},
)


@router.get("/api/v1/site_info")
async def site_info(
    user_name=Depends(get_user_from_header), session=Depends(get_db_session)
):

    if not user_name:
        raise HTTPException(status_code=403, detail="Unknown requester")

    # send timezone
    timezone = os.environ["PGTZ"]

    all_fleets = session.get_all_fleets()
    fleet_list = [fleet.name for fleet in all_fleets]

    response = {"fleet_names": fleet_list, "timezone": timezone}

    return response


@router.post("/api/v1/master_data/fleet")
async def master_data(
    master_data_info: MasterDataInfo,
    user_name=Depends(get_user_from_header),
    session=Depends(get_db_session),
):

    if not user_name:
        raise HTTPException(status_code=403, detail="Unknown requester")

    all_fleets = session.get_all_fleets()
    fleet_list = [fleet.name for fleet in all_fleets]

    if master_data_info.fleet_name not in fleet_list:
        raise HTTPException(status_code=403, detail="Unknown fleet")

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


# temporary addition for first release
# TODO : remove viewable code after frontend is enabled to read sherpa_summary
@router.get("/api/v1/sherpa_summary/{sherpa_name}/{viewable}")
async def sherpa_summary(
    sherpa_name: str, viewable: int, user_name=Depends(get_user_from_header)
):
    response = {}

    try:
        recent_events: List[SherpaEvent] = session.get_sherpa_events(sherpa_name)
        result = []
        for recent_event in recent_events:
            temp = recent_event.__dict__
            del temp["_sa_instance_state"]
            del temp["updated_at"]
            temp["created_at"] = dt_to_str(temp["created_at"])

            result.append(temp)
        response.update({"recent_events": {"events": result}})

    except Exception as e:
        response.update({"recent_events": {"error": e}})

    try:
        sherpa: Sherpa = session.get_sherpa(sherpa_name)
        response.update({"sherpa": fu.get_table_as_dict(Sherpa, sherpa)})
    except Exception as e:
        response.update({"sherpa": {"error": e}})
    try:
        sherpa_status: SherpaStatus = session.get_sherpa_status(sherpa_name)
        response.update(
            {"sherpa_status": fu.get_table_as_dict(SherpaStatus, sherpa_status)}
        )
    except Exception as e:
        response.update({"sherpa_status": {"error": e}})

    if viewable:
        df = pd.DataFrame(data=response)
        df = df.fillna(" ")
        response = df.to_html()
        return HTMLResponse(content=response, status_code=200)

    return response


@router.post("/api/v1/trips/get_route_wps")
async def get_route_wps(
    route_preview_req: RoutePreview,
    user_name=Depends(get_user_from_header),
):
    if not user_name:
        raise HTTPException(status_code=403, detail="Unknown requester")
    stations_poses = []
    fleet_name = route_preview_req.fleet_name
    for station_name in route_preview_req.route:
        station = session.get_station(station_name)
        stations_poses.append(station.pose)

    pass
