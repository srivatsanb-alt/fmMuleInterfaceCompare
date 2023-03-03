import requests
import redis
import os
import json
import redis
import os
import json
from typing import Union
from core.constants import FleetStatus, DisabledReason
from utils.comms import get_sherpa_url
from fastapi import APIRouter, Depends
from models.db_session import DBSession
import models.request_models as rqm
import models.fleet_models as fm
from app.routers.dependencies import (
    get_user_from_header,
    process_req_with_response,
    raise_error,
import models.request_models as rqm
import models.fleet_models as fm
from app.routers.dependencies import (
    get_user_from_header,
    process_req_with_response,
    raise_error,
)


router = APIRouter(
    prefix="/api/v1/control",
    tags=["control"],
    responses={404: {"description": "Not found"}},
)

# clears visa assignments- traffic zones which cannot be accessed by more than one sherpa at a time.
# clears visa assignments- traffic zones which cannot be accessed by more than one sherpa at a time.
# Only one sherpa is assigned a visa to that zone, and after the completion of it's trip
# the visa is revoked.


@router.get("/fleet/clear_all_visa_assignments")
async def clear_all_visa_assignments(user_name=Depends(get_user_from_header)):

    if not user_name:
        raise_error("Unknown requester", 401)

    delete_visas_req = rqm.DeleteVisaAssignments()
    delete_visas_req = rqm.DeleteVisaAssignments()
    response = process_req_with_response(None, delete_visas_req, user_name)

    return response


# returns the sherpa status(name, assigned, initialized, idle, disabled, inducted, etc.)

# returns the sherpa status(name, assigned, initialized, idle, disabled, inducted, etc.)
@router.get("/sherpa/{entity_name}/diagnostics")
async def diagnostics(
    entity_name=Union[str, None],
    user_name=Depends(get_user_from_header),
):

    response = {}

    if not user_name:
        raise_error("Unknown requester", 401)

    if not entity_name:
        raise_error("No entity name")

    with DBSession() as dbsession:
        sherpa_status = dbsession.get_sherpa_status(entity_name)
        if not sherpa_status:
            raise_error("Bad sherpa name")

        if not sherpa_status.sherpa.ip_address:
            raise_error("Sherpa not yet connected to the fleet manager")

        diagnostics_req = rqm.DiagnosticsReq(sherpa_name=entity_name)
        base_url, verify = get_sherpa_url(sherpa_status.sherpa)
        url = f"{base_url}/{diagnostics_req.endpoint}"
        response = requests.get(url, verify=verify)

        if response.status_code == 200:
            response = response.json()
        else:
            raise_error(f"Bad response from sherpa, {response.status_code}")

    return response


# restarts the mule docker container.
@router.get("/sherpa/{entity_name}/restart_mule_docker")
async def restart_mule_docker(
    entity_name=Union[str, None],
    user_name=Depends(get_user_from_header),
):

    response = {}

    if not user_name:
        raise_error("Unknown requester", 401)

    if not entity_name:
        raise_error("No entity name")

    with DBSession() as dbsession:
        sherpa_status = dbsession.get_sherpa_status(entity_name)

        if not sherpa_status.sherpa.ip_address:
            raise_error("Sherpa not yet connected to the fleet manager")

        base_url, verify = get_sherpa_url(sherpa_status.sherpa)
        url = f"{base_url}/restart_mule_docker"
        response = requests.get(url, verify=verify)

        if response.status_code == 200:
            response = response.json()
        else:
            raise_error(f"Bad response from sherpa, {response.status_code}")

    return response


# updates sherpa docker image
@router.get("/sherpa/{entity_name}/update_sherpa_img")
async def update_sherpa_img(
    entity_name=Union[str, None],
    user_name=Depends(get_user_from_header),
):

    response = {}

    if not user_name:
        raise_error("Unknown requester", 401)

    if not entity_name:
        raise_error("No entity name")

    with DBSession() as dbsession:
        sherpa_status = dbsession.get_sherpa_status(entity_name)

        if not sherpa_status.sherpa.ip_address:
            raise_error("Sherpa not yet connected to the fleet manager")

        update_image_req = rqm.SherpaImgUpdateCtrlReq(sherpa_name=entity_name)
        _ = process_req_with_response(None, update_image_req, user_name)

    return response


# starts or stops the fleet
# starts or stops the fleet
@router.post("/fleet/{entity_name}/start_stop")
async def start_stop(
    start_stop_ctrl_req: rqm.StartStopCtrlReq,
    entity_name=Union[str, None],
    user_name=Depends(get_user_from_header),
):

    response = {}

    if not user_name:
        raise_error("Unknown requester", 401)

    if not entity_name:
        raise_error(detail="No entity name")

    with DBSession() as dbsession:
        fleet: fm.Fleet = dbsession.get_fleet(entity_name)
        if not fleet:
            raise_error("Fleet not found")

        fleet.status = (
            FleetStatus.STARTED if start_stop_ctrl_req.start else FleetStatus.STOPPED
        )

    return response


# to emergency stop the fleet
@router.post("/fleet/{entity_name}/emergency_stop")
async def emergency_stop(
    pause_resume_ctrl_req: rqm.PauseResumeCtrlReq,
    entity_name=Union[str, None],
    user_name=Depends(get_user_from_header),
):

    response = {}

    if not user_name:
        raise_error("Unknown requester", 401)

    if not entity_name:
        raise_error("No entity name")

    with DBSession() as dbsession:
        fleet: fm.Fleet = dbsession.get_fleet(entity_name)
        if not fleet:
            raise_error("Fleet not found")

        fleet.status = (
            FleetStatus.PAUSED if pause_resume_ctrl_req.pause else FleetStatus.STARTED
        )

        all_sherpa_status = dbsession.get_all_sherpa_status()
        unconnected_sherpas = []
        for sherpa_status in all_sherpa_status:
            sherpa_status.disabled = pause_resume_ctrl_req.pause
            if pause_resume_ctrl_req.pause:
                sherpa_status.disabled_reason = DisabledReason.EMERGENCY_STOP
            else:
                sherpa_status.disabled_reason = None

            pause_resume_req = rqm.PauseResumeReq(
                pause=pause_resume_ctrl_req.pause, sherpa_name=sherpa_status.sherpa_name
            )

            try:
                _ = process_req_with_response(None, pause_resume_req, user_name)
            except Exception as e:
                unconnected_sherpas.append([sherpa_status.sherpa_name, e])

    return response


# to emergency stop the sherpa
@router.post("/sherpa/{entity_name}/emergency_stop")
async def sherpa_emergency_stop(
    pause_resume_ctrl_req: rqm.PauseResumeCtrlReq,
    entity_name: str,
    user_name=Depends(get_user_from_header),
):

    response = {}

    if not user_name:
        raise_error("Unknown requester", 401)

    if not entity_name:
        raise_error("No entity name")

    with DBSession() as dbsession:
        sherpa_status: fm.SherpaStatus = dbsession.get_sherpa_status(entity_name)
        if not sherpa_status:
            raise_error("Bad sherpa name")

        if not sherpa_status.sherpa.ip_address:
            raise_error("Sherpa not yet connected to the fleet manager")

        fleet_name = sherpa_status.sherpa.fleet.name
        fleet_status = dbsession.get_fleet(fleet_name)

        if fleet_status.status == "emergency_stop":
            raise_error("Start/resume fleet to resume/pause sherpas")

        sherpa_status.disabled = pause_resume_ctrl_req.pause
        if pause_resume_ctrl_req.pause:
            sherpa_status.disabled_reason = DisabledReason.EMERGENCY_STOP
        else:
            sherpa_status.disabled_reason = None

        pause_resume_req = rqm.PauseResumeReq(
            pause=pause_resume_ctrl_req.pause, sherpa_name=entity_name
        )

    _ = process_req_with_response(None, pause_resume_req, user_name)

    return response


# switches mode of the sherpa - (various modes - manual, fleet, remote, simulation etc)
@router.post("/sherpa/{entity_name}/switch_mode")
async def switch_mode(
    switch_mode_ctrl_req: rqm.SwitchModeCtrlReq,
    entity_name=Union[str, None],
    user_name=Depends(get_user_from_header),
):

    response = {}

    if not user_name:
        raise_error("Unknown requester", 401)

    if not entity_name:
        raise_error("No entity name")

    with DBSession() as dbsession:
        sherpa_status = dbsession.get_sherpa_status(entity_name)

        if not sherpa_status:
            raise_error("Bad sherpa name")

        if not sherpa_status.sherpa.ip_address:
            raise_error("Sherpa not yet connected to the fleet manager")

        switch_mode_req = rqm.SwitchModeReq(
            mode=switch_mode_ctrl_req.mode, sherpa_name=entity_name
        )

    _ = process_req_with_response(None, switch_mode_req, user_name)

    return response


# resets the position of sherpa to the station specified by the user
@router.post("/sherpa/{entity_name}/recovery")
async def reset_pose(
    reset_pose_ctrl_req: rqm.ResetPoseCtrlReq,
    entity_name=Union[str, None],
    user_name=Depends(get_user_from_header),
):

    response = {}

    if not user_name:
        raise_error("Unknown requester", 401)

    if not entity_name:
        raise_error("No entity name")

    if not reset_pose_ctrl_req.fleet_station:
        raise_error("No fleet staion detail")

    with DBSession() as dbsession:
        sherpa_status = dbsession.get_sherpa_status(entity_name)
        if not sherpa_status:
            raise_error("Bad sherpa name")

        if not sherpa_status.sherpa.ip_address:
            raise_error("Sherpa not yet connected to the fleet manager")

        station = dbsession.get_station(reset_pose_ctrl_req.fleet_station)

        if not station:
            raise_error("Bad fleet staion detail")

        reset_pose_req = rqm.ResetPoseReq(
            pose=station.pose,
            sherpa_name=entity_name,
        )

    _ = process_req_with_response(None, reset_pose_req, user_name)

    return response


# inducts sherpa into the fleet
# trips not assigned otherwise
@router.post("/sherpa/{sherpa_name}/induct")
async def induct_sherpa(
    sherpa_name: str,
    sherpa_induct_req: rqm.SherpaInductReq,
    user_name=Depends(get_user_from_header),
):
    respone = {}
    sherpa_induct_req.sherpa_name = sherpa_name

    with DBSession() as dbsession:
        sherpa = dbsession.get_sherpa(sherpa_name)

        if not sherpa.ip_address:
            raise_error("Sherpa not yet connected to the fleet manager")

        if sherpa.status.pose is None:
            raise_error(f"Cannot induct a {sherpa_name} into fleet, sherpa pose is None")

        if sherpa.status.trip_id and not sherpa_induct_req.induct:
            trip = dbsession.get_trip(sherpa.status.trip_id)
            raise_error(
                f"delete the ongoing trip with booking_id: {trip.booking_id}, to induct {sherpa_name} out of fleet"
            )

    _ = process_req_with_response(None, sherpa_induct_req, user_name)

    return respone


@router.get("/restart_fleet_manager")
def restart_fm(user_name=Depends(get_user_from_header)):
    response = {}
    if not user_name:
        raise_error("Unknown requester", 401)

    redis_conn = redis.from_url(os.getenv("FM_REDIS_URI"))
    redis_conn.set("restart_fm", json.dumps(True))

    return response
