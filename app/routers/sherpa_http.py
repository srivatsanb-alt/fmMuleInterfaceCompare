import os
import time

import redis

from app.routers.dependencies import get_sherpa
from core.config import Config
from endpoints.request_models import (
    InitMsg,
    ReachedReq,
    SherpaPeripheralsReq,
    SherpaReq,
    VerifyFleetFilesResp,
)
from fastapi import APIRouter, Depends, HTTPException
from rq.job import Job
from utils.rq import Queues, enqueue

router = APIRouter(
    prefix="/api/v1/sherpa",
    tags=["sherpa"],
    # dependencies=[Depends(get_sherpa)],
    responses={404: {"description": "Not found"}},
)


def process_msg(msg: SherpaReq, sherpa: str):
    if sherpa is None:
        raise HTTPException(status_code=403, detail="Unknown sherpa")
    handler_obj = Config.get_handler()
    msg.source = sherpa

    return enqueue(Queues.handler_queue, handle, handler_obj, msg)


@router.post("/init/")
async def init_sherpa(init_msg: InitMsg, sherpa: str = Depends(get_sherpa)):
    process_msg(init_msg, sherpa)


@router.post("/trip/reached/")
async def reached(reached_msg: ReachedReq, sherpa: str = Depends(get_sherpa)):
    process_msg(reached_msg, sherpa)


@router.post("/peripherals/")
async def peripherals(
    peripherals_req: SherpaPeripheralsReq, sherpa: str = Depends(get_sherpa)
):
    process_msg(peripherals_req, sherpa)


@router.get("/verify_fleet_files", response_model=VerifyFleetFilesResp)
async def verify_fleet_files(sherpa: str = Depends(get_sherpa)):
    job: Job = process_msg(
        SherpaReq(type="verify_fleet_files", timestamp=time.time()), sherpa
    )
    redis_conn = redis.from_url(os.getenv("FM_REDIS_URI"))
    while True:
        status = Job.fetch(job.id, connection=redis_conn).get_status(refresh=True)
        if status == "finished":
            response = Job.fetch(job.id, connection=redis_conn).result
            break
        if status == "failed":
            raise HTTPException(status_code=500)
        time.sleep(1)
    return VerifyFleetFilesResp.from_json(response)


def handle(handler, msg):
    return handler.handle(msg)
