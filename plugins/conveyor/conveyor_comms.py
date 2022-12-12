import asyncio
import hashlib
from fastapi import APIRouter, WebSocket
from plugins.plugin_comms import ws_reader, ws_writer
from fastapi import Depends, Header
from .conveyor_utils import ConvTrips, ConvInfo, session
from .conveyor_handler import CONV_HANDLER
import logging

router = APIRouter()


def get_conveyor(x_api_key: str = Header(None)):
    if x_api_key is None:
        return None
    logging.info(f"API key: {x_api_key}")
    return None

    hashed_api_key = hashlib.sha256(x_api_key.encode("utf-8")).hexdigest()
    info: ConvInfo = (
        session.query(ConvInfo).filter(hashed_api_key=ConvInfo.api_key).one_or_none()
    )
    if info:
        conveyor = info["name"]  # make this file!
    else:
        conveyor = None
    return conveyor


@router.get("/plugin/ws/api/v1/plugin_conveyor")
async def check_connection():
    return {"uvicorn": "I Am Alive"}


@router.get("/plugin/ws/api/v1/conveyor_info")
async def conveyor_info():
    db_info: ConvInfo = session.Query(ConvInfo).all()
    return db_info


@router.get("/plugin/ws/api/v1/conveyor_trips")
async def conveyor_trips():
    db_info: ConvInfo = session.Query(ConvTrips).all()
    return db_info


@router.websocket("/plugin/ws/api/v1/conveyor")
async def conveyor_ws(
    websocket: WebSocket,
):  # get conveyor station name from Header (Depends)

    await websocket.accept()
    conveyor_name = "Conveyor1"
    conv_handler = CONV_HANDLER()
    rw = [
        asyncio.create_task(
            ws_reader(websocket, "conveyor", conv_handler, unique_id=conveyor_name)
        ),
        asyncio.create_task(
            ws_writer(websocket, "conveyor", unique_id=conveyor_name, format="text"),
        ),
    ]
    try:
        await asyncio.gather(*rw)
    finally:
        [t.cancel() for t in rw]
