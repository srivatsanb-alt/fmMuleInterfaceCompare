from app.routers.dependencies import get_sherpa

from core.config import Config
from endpoints.request_models import (
    InitMsg,
    ReachedReq,
    SherpaPeripheralsReq,
    SherpaReq,
)
from fastapi import APIRouter, Depends, HTTPException
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

    enqueue(Queues.handler_queue, handle, handler_obj, msg)


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


def handle(handler, msg):
    handler.handle(msg)
