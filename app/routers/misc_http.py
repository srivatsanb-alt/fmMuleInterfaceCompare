import os
import time
import redis
from app.routers.dependencies import get_user_from_header
from core.config import Config
from models.request_models import (
    FleetInfoRequest
)
from models.db_session import session
from fastapi import APIRouter, Depends, HTTPException

router = APIRouter(
    responses={404: {"description": "Not found"}},
)


@router.post("/api/v1/info/fleet")
async def fleet_info(fleet_info_req: FleetInfoRequest,
                     user=Depends(get_user_from_header)):

    response = {}
    db_sherpas = session.get_all_sherpas()
    db_stations = session.get_all_stations()

    sherpa_list = [sherpa.name
                   for sherpa in db_sherpas
                   if sherpa.fleet.name == fleet_info_req.fleet_name
                   ]

    station_list = [station.name
                    for station in db_stations
                    if station.fleet.name == fleet_info_req.fleet_name
                    ]

    response.update({"sherpa_list": sherpa_list})
    response.update({"station_list": station_list})

    return response
