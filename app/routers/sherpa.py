import hashlib
import importlib

from core import config
from core.db import session_maker
from fastapi import APIRouter, Depends, HTTPException, Header
from models.fleet_models import Sherpa
from utils.rq import Queues, enqueue

from endpoints.request_models import InitMsg


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


@router.post("/init/")
async def init_sherpa(init_msg: InitMsg, sherpa: str = Depends(get_sherpa)):
    if sherpa is None:
        raise HTTPException(status_code=403, detail="Unknown sherpa")
    handler_package = config.get_handler_package()
    handler_class = config.get_handler_class()
    handler_obj = getattr(importlib.import_module(handler_package), handler_class)()
    init_msg.source = sherpa

    enqueue(Queues.handler_queue, handle, handler_obj, init_msg)


def handle(handler, msg):
    handler.handle(msg)
