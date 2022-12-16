import asyncio
import hashlib
from fastapi import APIRouter, WebSocket
from plugins.plugin_comms import ws_reader, ws_writer
from fastapi import Depends, Header, status
from .conveyor_utils import ConvTrips, ConvInfo, session
from .conveyor_handler import CONV_HANDLER

router = APIRouter()


def get_conveyor(x_api_key: str = Header(None)):
    conveyor_name = None
    if x_api_key is None:
        return None

    hashed_api_key = hashlib.sha256(x_api_key.encode("utf-8")).hexdigest()
    conv_info: ConvInfo = (
        session.query(ConvInfo)
        .filter(ConvInfo.hashed_api_key == hashed_api_key)
        .one_or_none()
    )

    if conv_info is not None:
        conveyor_name = conv_info.name

    return conveyor_name


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
async def conveyor_ws(websocket: WebSocket, conveyor_name=Depends(get_conveyor)):

    if conveyor_name is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()

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
