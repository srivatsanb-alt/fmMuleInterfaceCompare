from fastapi import APIRouter, Depends
from typing import Union
from models.db_session import DBSession
from utils import fleet_utils as fu
from utils.comms import close_websocket_for_sherpa
from core.constants import FleetStatus
from models.fleet_models import Fleet, Sherpa, SherpaStatus, AvailableSherpas
from app.routers.dependencies import (
    get_user_from_header,
    raise_error,
)

router = APIRouter(
    prefix="/api/v1/configure_fleet",
    tags=["configure_fleet"],
    responses={404: {"description": "Not found"}},
)


@router.get("/reset/fleet/{fleet_name}")
async def reset_fleet(
    fleet_name=Union[str, None],
    username=Depends(get_user_from_header),
):
    response = {}
    fleet_name = fleet_name

    if not username:
        raise_error("Unknown requester")

    if not fleet_name:
        raise_error("No fleet name")

    with DBSession() as dbsession:
        fleet: Fleet = dbsession.get_fleet(fleet_name)
        fleet.status = FleetStatus.STOPPED
        dbsession.session.commit()

        fu.reset_fleet(dbsession, fleet_name)
        all_fleet_sherpas = dbsession.get_all_sherpas_in_fleet(fleet_name)

        # close ws connection to make sure new map files are downloaded by sherpa on reconnect
        for sherpa in all_fleet_sherpas:
            close_websocket_for_sherpa(sherpa.name)

    return response


@router.get("/delete/sherpa/{sherpa_name}")
async def diagnostics(
    sherpa_name=Union[str, None],
    username=Depends(get_user_from_header),
):
    response = {}

    if not username:
        raise_error("Unknown requester")

    if not sherpa_name:
        raise_error("No sherpa_name")

    with DBSession() as dbsession:
        sherpa_status: SherpaStatus = dbsession.get_sherpa_status(sherpa_name)

        if not sherpa_status:
            raise_error("Invalid sherpa name")

        # close ws connection
        close_websocket_for_sherpa(sherpa_name)

        # delete sherpa status
        dbsession.session.delete(sherpa_status)

        # delete sherpa
        sherpa: Sherpa = dbsession.get_sherpa(sherpa_name)
        dbsession.session.delete(sherpa)

        # delete sherpa entry in AvailableSherpas
        dbsession.session.query(AvailableSherpas).filter(
            AvailableSherpas.sherpa_name == sherpa_name
        ).delete()

    return response
