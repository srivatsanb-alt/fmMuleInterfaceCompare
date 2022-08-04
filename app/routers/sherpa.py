import hashlib
import importlib
from core.config import Config

from core.db import session_maker
from fastapi import APIRouter, Depends, HTTPException, Header
from models.fleet_models import Sherpa
from utils.rq import Queues, enqueue

from endpoints.request_models import InitMsg, ReachedMsg, SherpaMsg


def get_sherpa(x_api_key: str = Header(None)):
    if x_api_key is None:
        return None
    db = session_maker()
    hashed_api_key = hashlib.sha256(x_api_key.encode("utf-8")).hexdigest()
    db_sherpa: Sherpa = (
        db.query(Sherpa).filter(Sherpa.hashed_api_key == hashed_api_key).one_or_none()
    )
    return db_sherpa.name if db_sherpa else None


router = APIRouter(
    prefix="/api/v1/sherpa",
    tags=["sherpa"],
    # dependencies=[Depends(get_sherpa)],
    responses={404: {"description": "Not found"}},
)


def process_msg(msg: SherpaMsg, sherpa: str):
    if sherpa is None:
        raise HTTPException(status_code=403, detail="Unknown sherpa")
    handler_package = Config.get_handler_package()
    handler_class = Config.get_handler_class()
    handler_obj = getattr(importlib.import_module(handler_package), handler_class)()
    msg.source = sherpa

    enqueue(Queues.handler_queue, handle, handler_obj, msg)


@router.post("/init/")
async def init_sherpa(init_msg: InitMsg, sherpa: str = Depends(get_sherpa)):
    process_msg(init_msg, sherpa)


@router.post("/reached/")
async def reached(reached_msg: ReachedMsg, sherpa: str = Depends(get_sherpa)):
    process_msg(reached_msg, sherpa)


def handle(handler, msg):
    handler.handle(msg)
