import hashlib
import importlib
from typing import Optional

from app import app
from core import config
from core.db import session_maker
from fastapi import Depends, Header, HTTPException
from models.fleet_models import Sherpa
from sqlalchemy.orm import Session
from utils.rq import Queues, enqueue

from endpoints.request_models import InitMsg


def get_sherpa(
    x_api_key: Optional[str] = Header(None), db: Session = Depends(session_maker)
):
    if x_api_key is None:
        return None
    hashed_api_key = hashlib.sha256(x_api_key.encode("utf-8")).hexdigest()
    return db.query(Sherpa).filter(Sherpa.hashed_api_key == hashed_api_key).one_or_none()


@app.post("/sherpa/init")
async def init_sherpa(init_msg: InitMsg, sherpa: str = Depends(get_sherpa)):
    if sherpa is None:
        raise HTTPException(status_code=403, detail="Unknown sherpa")
    handler_package = config.get_handler_package
    handler_class = config.get_handler_class
    handler_obj = getattr(importlib.import_module(handler_package), handler_class)()

    enqueue(Queues.handler_queue, handler_obj, init_msg, name=sherpa)
