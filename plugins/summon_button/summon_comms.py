import asyncio
import hashlib
from fastapi import APIRouter, WebSocket, Depends, Header, status
from plugins.plugin_comms import ws_reader, ws_writer
from .summon_models import SummonInfo, DBSession
from .summon_handler import SUMMON_HANDLER

router = APIRouter()


def get_summon(x_api_key: str = Header(None)):
    #     with DBSession() as dbsession:
    #         summon_info: SummonInfo = (
    #                 dbsession.session.query(SummonInfo)
    #                 .filter(SummonInfo.hashed_api_key == "38904cded54aebda0db5c4bb1295f26a9e859cc4befebbe323ad63c009aca434")
    #                 .one_or_none()
    #             )

    #     return summon_info

    if x_api_key is None:
        return None

    hashed_api_key = hashlib.sha256(x_api_key.encode("utf-8")).hexdigest()
    with DBSession() as dbsession:
        summon_info: SummonInfo = (
            dbsession.session.query(SummonInfo)
            .filter(SummonInfo.hashed_api_key == hashed_api_key)
            .one_or_none()
        )
    return summon_info


@router.get("/plugin/ws/api/v1/plugin_summon_button")
async def check_connection():
    return {"uvicorn": "I Am Alive"}


@router.websocket("/plugin/ws/api/v1/summon")
async def summon_button_ws(websocket: WebSocket, summon_info=Depends(get_summon)):
    if not summon_info:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()

    summon_handler = SUMMON_HANDLER()
    rw = [
        asyncio.create_task(ws_reader(websocket, "summon_button", summon_handler)),
        asyncio.create_task(
            ws_writer(websocket, "summon_button", format="text"),
        ),
    ]
    try:
        await asyncio.gather(*rw)
    finally:
        [t.cancel() for t in rw]
