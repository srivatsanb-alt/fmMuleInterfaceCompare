import requests
from typing import Union
from app.routers.dependencies import (
    get_user_from_header,
    process_req,
    process_req_with_response,
)
from core.constants import FleetStatus, DisabledReason
from models.fleet_models import Fleet, SherpaStatus

from utils.comms import get_sherpa_url
from fastapi import APIRouter, Depends, HTTPException
from models.db_session import session
from models.request_models import (
    PauseResumeReq,
    SwitchModeReq,
    DiagnosticsReq,
    ResetPoseReq,
    PauseResumeCtrlReq,
    SwitchModeCtrlReq,
    ResetPoseCtrlReq,
    StartStopCtrlReq,
    SherpaInductReq,
    DeleteVisaAssignments,
    SherpaImgUpdateCtrlReq,
)


router = APIRouter(
    prefix="/api/v1/control",
    tags=["control"],
    responses={404: {"description": "Not found"}},
)


def handle(handler, msg):
    handler.handle(msg)


@router.get("/fleet/clear_all_visa_assignments")
async def clear_all_visa_assignments(user_name=Depends(get_user_from_header)):

    if not user_name:
        raise HTTPException(status_code=403, detail="Unknown requester")

    delete_visas_req = DeleteVisaAssignments()
    response = process_req_with_response(None, delete_visas_req, user_name)

    return response


@router.get("/sherpa/{entity_name}/diagnostics")
async def diagnostics(
    entity_name=Union[str, None],
    user_name=Depends(get_user_from_header),
):

    response = {}

    if not user_name:
        raise HTTPException(status_code=403, detail="Unknown requester")

    if not entity_name:
        raise HTTPException(status_code=403, detail="No entity name")

    sherpa_status = session.get_sherpa_status(entity_name)
    if not sherpa_status:
        raise HTTPException(status_code=403, detail="Bad sherpa name")

    if not sherpa_status.sherpa.ip_address:
        raise HTTPException(
            status_code=403, detail="Sherpa not yet connected to the fleet manager"
        )

    diagnostics_req = DiagnosticsReq(sherpa_name=entity_name)
    base_url = get_sherpa_url(sherpa_status.sherpa)
    url = f"{base_url}/{diagnostics_req.endpoint}"
    response = requests.get(url)

    if response.status_code == 200:
        response = response.json()

    else:
        raise HTTPException(
            status_code=403, detail=f"Bad response from sherpa, {response.status_code}"
        )

    return response


@router.get("/sherpa/{entity_name}/update_sherpa_img")
async def update_sherpa_img(
    entity_name=Union[str, None],
    user_name=Depends(get_user_from_header),
):

    response = {}

    if not user_name:
        raise HTTPException(status_code=403, detail="Unknown requester")

    if not entity_name:
        raise HTTPException(status_code=403, detail="No entity name")

    sherpa_status = session.get_sherpa_status(entity_name)

    if not sherpa_status.sherpa.ip_address:
        raise HTTPException(
            status_code=403, detail="Sherpa not yet connected to the fleet manager"
        )

    update_image_req = SherpaImgUpdateCtrlReq(sherpa_name=entity_name)
    _ = process_req_with_response(None, update_image_req, user_name)

    return response


@router.post("/fleet/{entity_name}/start_stop")
async def start_stop(
    start_stop_ctrl_req: StartStopCtrlReq,
    entity_name=Union[str, None],
    user_name=Depends(get_user_from_header),
):

    response = {}

    if not user_name:
        raise HTTPException(status_code=403, detail="Unknown requester")

    if not entity_name:
        raise HTTPException(status_code=403, detail="No entity name")

    fleet: Fleet = session.get_fleet(entity_name)
    if not fleet:
        raise HTTPException(status_code=403, detail="Fleet not found")

    fleet.status = FleetStatus.STARTED if start_stop_ctrl_req.start else FleetStatus.STOPPED
    session.close()

    return response


@router.post("/fleet/{entity_name}/emergency_stop")
async def emergency_stop(
    pause_resume_ctrl_req: PauseResumeCtrlReq,
    entity_name=Union[str, None],
    user_name=Depends(get_user_from_header),
):

    response = {}

    if not user_name:
        raise HTTPException(status_code=403, detail="Unknown requester")

    if not entity_name:
        raise HTTPException(status_code=403, detail="No entity name")

    fleet: Fleet = session.get_fleet(entity_name)
    if not fleet:
        raise HTTPException(status_code=403, detail="Fleet not found")

    fleet.status = (
        FleetStatus.PAUSED if pause_resume_ctrl_req.pause else FleetStatus.STARTED
    )

    all_sherpa_status = session.get_all_sherpa_status()
    unconnected_sherpas = []
    for sherpa_status in all_sherpa_status:
        sherpa_status.disabled = pause_resume_ctrl_req.pause
        if pause_resume_ctrl_req.pause:
            sherpa_status.disabled_reason = DisabledReason.EMERGENCY_STOP
        else:
            sherpa_status.disabled_reason = None

        pause_resume_req = PauseResumeReq(
            pause=pause_resume_ctrl_req.pause, sherpa_name=sherpa_status.sherpa_name
        )

        try:
            _ = process_req_with_response(None, pause_resume_req, user_name)
        except Exception as e:
            unconnected_sherpas.append([sherpa_status.sherpa_name, e])
    session.close()

    return response


@router.post("/sherpa/{entity_name}/emergency_stop")
async def sherpa_emergency_stop(
    pause_resume_ctrl_req: PauseResumeCtrlReq,
    entity_name: str,
    user_name=Depends(get_user_from_header),
):

    response = {}

    if not user_name:
        raise HTTPException(status_code=403, detail="Unknown requester")

    if not entity_name:
        raise HTTPException(status_code=403, detail="No entity name")

    sherpa_status: SherpaStatus = session.get_sherpa_status(entity_name)
    if not sherpa_status:
        raise HTTPException(status_code=403, detail="Bad sherpa name")

    if not sherpa_status.sherpa.ip_address:
        raise HTTPException(
            status_code=403, detail="Sherpa not yet connected to the fleet manager"
        )

    fleet_name = sherpa_status.sherpa.fleet.name
    fleet_status = session.get_fleet(fleet_name)

    if fleet_status.status == "emergency_stop":
        raise HTTPException(
            status_code=403, detail="Start/resume fleet to resume/pause sherpas"
        )

    sherpa_status.disabled = pause_resume_ctrl_req.pause
    if pause_resume_ctrl_req.pause:
        sherpa_status.disabled_reason = DisabledReason.EMERGENCY_STOP
    else:
        sherpa_status.disabled_reason = None

    pause_resume_req = PauseResumeReq(
        pause=pause_resume_ctrl_req.pause, sherpa_name=entity_name
    )

    _ = process_req_with_response(None, pause_resume_req, user_name)

    session.close()

    return response


@router.post("/sherpa/{entity_name}/switch_mode")
async def switch_mode(
    switch_mode_ctrl_req: SwitchModeCtrlReq,
    entity_name=Union[str, None],
    user_name=Depends(get_user_from_header),
):

    response = {}

    if not user_name:
        raise HTTPException(status_code=403, detail="Unknown requester")

    if not entity_name:
        raise HTTPException(status_code=403, detail="No entity name")

    sherpa_status = session.get_sherpa_status(entity_name)

    if not sherpa_status:
        raise HTTPException(status_code=403, detail="Bad sherpa name")

    if not sherpa_status.sherpa.ip_address:
        raise HTTPException(
            status_code=403, detail="Sherpa not yet connected to the fleet manager"
        )

    switch_mode_req = SwitchModeReq(mode=switch_mode_ctrl_req.mode, sherpa_name=entity_name)
    _ = process_req_with_response(None, switch_mode_req, user_name)

    return response


@router.post("/sherpa/{entity_name}/recovery")
async def reset_pose(
    reset_pose_ctrl_req: ResetPoseCtrlReq,
    entity_name=Union[str, None],
    user_name=Depends(get_user_from_header),
):

    response = {}

    if not user_name:
        raise HTTPException(status_code=403, detail="Unknown requester")

    if not entity_name:
        raise HTTPException(status_code=403, detail="No entity name")

    if not reset_pose_ctrl_req.fleet_station:
        raise HTTPException(status_code=403, detail="No fleet staion detail")

    sherpa_status = session.get_sherpa_status(entity_name)
    if not sherpa_status:
        raise HTTPException(status_code=403, detail="Bad sherpa name")

    if not sherpa_status.sherpa.ip_address:
        raise HTTPException(
            status_code=403, detail="Sherpa not yet connected to the fleet manager"
        )

    station = session.get_station(reset_pose_ctrl_req.fleet_station)

    if not station:
        raise HTTPException(status_code=403, detail="Bad fleet staion detail")

    reset_pose_req = ResetPoseReq(
        pose=station.pose,
        sherpa_name=entity_name,
    )

    _ = process_req_with_response(None, reset_pose_req, user_name)

    return response


@router.post("/sherpa/{sherpa_name}/induct")
async def induct_sherpa(
    sherpa_name: str,
    sherpa_induct_req: SherpaInductReq,
    user_name=Depends(get_user_from_header),
):
    respone = {}
    sherpa_induct_req.sherpa_name = sherpa_name
    sherpa = session.get_sherpa(sherpa_name)

    if sherpa.status.trip_id and not sherpa_induct_req.induct:
        trip = session.get_trip(sherpa.status.trip_id)
        raise HTTPException(
            status_code=403,
            detail=f"delete the ongoing trip with booking_id: {trip.booking_id}, to induct {sherpa_name} out of fleet",
        )

    _ = process_req_with_response(None, sherpa_induct_req, user_name)

    return respone
