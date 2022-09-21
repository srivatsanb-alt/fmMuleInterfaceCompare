import requests
import redis
import os
import datetime
import time
from rq.job import Job
from typing import Union
from app.routers.dependencies import get_user_from_header, get_db_session
from core.constants import FleetStatus, DisabledReason
from models.fleet_models import Fleet, SherpaStatus
from utils.comms import get_sherpa_url
from utils.rq import Queues, enqueue
from core.config import Config
from fastapi import APIRouter, Depends, HTTPException

from models.request_models import (
    PauseResumeReq,
    SwitchModeReq,
    DiagnosticsReq,
    ResetPoseReq,
    PauseResumeCtrlReq,
    SwitchModeCtrlReq,
    ResetPoseCtrlReq,
    StartStopCtrlReq,
)


router = APIRouter(
    prefix="/api/v1/control",
    tags=["control"],
    responses={404: {"description": "Not found"}},
)


def process_req(req, user: str):
    if not user:
        raise HTTPException(status_code=403, detail="Unknown user")

    handler_obj = Config.get_handler()
    return enqueue(Queues.handler_queue, handle, handler_obj, req)


def process_req_with_response(req, user: str):
    job: Job = process_req(req, user)
    redis_conn = redis.from_url(os.getenv("FM_REDIS_URI"))
    n_attempt = 1
    while True:
        status = Job.fetch(job.id, connection=redis_conn).get_status(refresh=True)
        if status == "finished":
            response = Job.fetch(job.id, connection=redis_conn).result
            break
        if status == "failed":
            time.sleep(1)
            job: Job = process_req(req, user)
            RETRY_ATTEMPTS = Config.get_rq_job_params()["http_retry_attempts"]
            if n_attempt > RETRY_ATTEMPTS:
                raise HTTPException(status_code=500, detail="rq job failed multiple times")
            n_attempt = n_attempt + 1
        time.sleep(0.1)
    return response


def handle(handler, msg):
    handler.handle(msg)


@router.post("/fleet/{entity_name}/start_stop")
async def start_stop(
    start_stop_ctrl_req: StartStopCtrlReq,
    entity_name=Union[str, None],
    user_name=Depends(get_user_from_header),
    session=Depends(get_db_session),
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

    return response


@router.post("/fleet/{entity_name}/emergency_stop")
async def emergency_stop(
    pause_resume_ctrl_req: PauseResumeCtrlReq,
    entity_name=Union[str, None],
    user_name=Depends(get_user_from_header),
    session=Depends(get_db_session),
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
            _ = process_req_with_response(pause_resume_req, user_name)
        except Exception as e:
            unconnected_sherpas.append([sherpa_status.sherpa_name, e])

    return response


@router.post("/sherpa/{entity_name}/emergency_stop")
async def sherpa_emergency_stop(
    pause_resume_ctrl_req: PauseResumeCtrlReq,
    entity_name=Union[str, None],
    user_name=Depends(get_user_from_header),
    session=Depends(get_db_session),
):

    response = {}

    if not user_name:
        raise HTTPException(status_code=403, detail="Unknown requester")

    if not entity_name:
        raise HTTPException(status_code=403, detail="No entity name")

    sherpa_status: SherpaStatus = session.get_sherpa_status(entity_name)
    if not sherpa_status:
        raise HTTPException(status_code=403, detail="Bad sherpa name")

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

    _ = process_req_with_response(pause_resume_req, user_name)

    return response


@router.post("/sherpa/{entity_name}/switch_mode")
async def switch_mode(
    switch_mode_ctrl_req: SwitchModeCtrlReq,
    entity_name=Union[str, None],
    user_name=Depends(get_user_from_header),
    session=Depends(get_db_session),
):

    response = {}

    if not user_name:
        raise HTTPException(status_code=403, detail="Unknown requester")

    if not entity_name:
        raise HTTPException(status_code=403, detail="No entity name")

    sherpa_status = session.get_sherpa_status(entity_name)

    if not sherpa_status:
        raise HTTPException(status_code=403, detail="Bad sherpa name")

    switch_mode_req = SwitchModeReq(mode=switch_mode_ctrl_req.mode, sherpa_name=entity_name)

    process_req(switch_mode_req, user_name)
    return response


@router.post("/sherpa/{entity_name}/recovery")
async def reset_pose(
    reset_pose_ctrl_req: ResetPoseCtrlReq,
    entity_name=Union[str, None],
    user_name=Depends(get_user_from_header),
    session=Depends(get_db_session),
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

    station = session.get_station(reset_pose_ctrl_req.fleet_station)

    if not station:
        raise HTTPException(status_code=403, detail="Bad fleet staion detail")

    reset_pose_req = ResetPoseReq(
        pose=station.pose,
        sherpa_name=entity_name,
    )

    _ = process_req_with_response(reset_pose_req, user_name)

    return response


@router.get("/sherpa/{entity_name}/diagnostics")
async def diagnostics(
    entity_name=Union[str, None],
    user_name=Depends(get_user_from_header),
    session=Depends(get_db_session),
):

    response = {}

    if not user_name:
        raise HTTPException(status_code=403, detail="Unknown requester")

    if not entity_name:
        raise HTTPException(status_code=403, detail="No entity name")

    sherpa_status = session.get_sherpa_status(entity_name)
    if not sherpa_status:
        raise HTTPException(status_code=403, detail="Bad sherpa name")

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
