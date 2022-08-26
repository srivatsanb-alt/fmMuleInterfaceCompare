import logging
from typing import Union
from app.routers.dependencies import (
        get_user_from_header,
        get_db_session
)
from utils.comms import send_msg_to_sherpa, get
from fastapi import APIRouter, Depends, HTTPException
from models.request_models import (
    PauseResumeReq,
    SwitchModeReq,
    DiagnosticsReq,
    ResetPoseReq,
    PauseResumeCtrlReq,
    SwitchModeCtrlReq,
    ResetPoseCtrlReq,
    StartStopCtrlReq
)

router = APIRouter(
    prefix="/api/v1/control",
    tags=["control"],
    responses={404: {"description": "Not found"}},
)


@router.post("/fleet/{entity_name}/start_stop")
async def start_stop(
            start_stop_ctrl_req: StartStopCtrlReq,
            entity_name=Union[str, None],
            user_name=Depends(get_user_from_header),
            session=Depends(get_db_session)
            ):

    response = {}

    if not user_name:
        raise HTTPException(status_code=403, detail="Unknown requester")

    if not entity_name:
        raise HTTPException(status_code=403, detail="No entity name")

    if start_stop_ctrl_req.start:
        session, _ = session.update_fleet_status(
                     entity_name, "start")
    else:
        session, _ = session.update_fleet_status(
                     entity_name, "stop")

    return response


@router.post("/fleet/{entity_name}/emergency_stop")
async def emergnecy_stop(
            pause_resume_ctrl_req: PauseResumeCtrlReq,
            entity_name=Union[str, None],
            user_name=Depends(get_user_from_header),
            session=Depends(get_db_session)
            ):

    response = {}

    if not user_name:
        raise HTTPException(status_code=403, detail="Unknown requester")

    if not entity_name:
        raise HTTPException(status_code=403, detail="No entity name")

    session, _ = session.update_fleet_status(
                     entity_name, "emergency_stop")

    all_sherpa_status = session.get_all_sherpa_status()
    for sherpa_status in all_sherpa_status:
        if sherpa_status.sherpa.fleet.name == entity_name:

            session, _ = session.enable_disable_sherpa(
                                sherpa_status.sherpa_name,
                                disable=pause_resume_ctrl_req.pause)
            pause_resume_req = PauseResumeReq(pause=pause_resume_ctrl_req.pause)
            send_msg_to_sherpa(sherpa_status.sherpa, pause_resume_req)

    return response


@router.post("/sherpa/{entity_name}/emergency_stop")
async def sherpa_emergnecy_stop(
            pause_resume_ctrl_req: PauseResumeCtrlReq,
            entity_name=Union[str, None],
            user_name=Depends(get_user_from_header),
            session=Depends(get_db_session)
            ):

    response = {}

    if not user_name:
        raise HTTPException(status_code=403, detail="Unknown requester")

    if not entity_name:
        raise HTTPException(status_code=403, detail="No entity name")

    sherpa_status = session.get_sherpa_status(entity_name)
    session, _ = session.enable_disable_sherpa(
                        sherpa_status.sherpa_name,
                        disable=pause_resume_ctrl_req.pause)

    pause_resume_req = PauseResumeReq(pause=pause_resume_ctrl_req.pause)
    send_msg_to_sherpa(sherpa_status.sherpa, pause_resume_req)

    return response


@router.post("/sherpa/{entity_name}/switch_mode")
async def switch_mode(
            switch_mode_ctrl_req: SwitchModeCtrlReq,
            entity_name=Union[str, None],
            user_name=Depends(get_user_from_header),
            session=Depends(get_db_session)
            ):

    response = {}

    if not user_name:
        raise HTTPException(status_code=403, detail="Unknown requester")

    if not entity_name:
        raise HTTPException(status_code=403, detail="No entity name")

    sherpa_status = session.get_sherpa_status(entity_name)
    switch_mode_req = SwitchModeReq(mode=switch_mode_ctrl_req.mode)
    send_msg_to_sherpa(sherpa_status.sherpa, switch_mode_req)

    return response


@router.post("/sherpa/{entity_name}/recovery")
async def reset_pose(
            reset_pose_ctrl_req: ResetPoseCtrlReq,
            entity_name=Union[str, None],
            user_name=Depends(get_user_from_header),
            session=Depends(get_db_session)
            ):

    response = {}

    if not user_name:
        raise HTTPException(status_code=403, detail="Unknown requester")

    if not entity_name:
        raise HTTPException(status_code=403, detail="No entity name")

    if not reset_pose_ctrl_req.fleet_station:
        raise HTTPException(status_code=403, detail="No fleet staion detail")

    sherpa_status = session.get_sherpa_status(entity_name)
    station = session.get_station(reset_pose_ctrl_req.fleet_station)

    if not station:
        raise HTTPException(status_code=403, detail="bad fleet staion detail")

    reset_pose_req = ResetPoseReq(pose=station.pose.to_lis)
    send_msg_to_sherpa(sherpa_status.sherpa, reset_pose_req)

    return response


@router.post("/sherpa/{entity_name}/diagnostics")
async def diagnostics(
            reset_pose_ctrl_req: ResetPoseCtrlReq,
            entity_name=Union[str, None],
            user_name=Depends(get_user_from_header),
            session=Depends(get_db_session)
            ):

    response = {}

    if not user_name:
        raise HTTPException(status_code=403, detail="Unknown requester")

    if not entity_name:
        raise HTTPException(status_code=403, detail="No entity name")

    sherpa_status = session.get_sherpa_status(entity_name)

    diagnostics_req = DiagnosticsReq()
    response = get(sherpa_status.sherpa, diagnostics_req)

    return response
