import asyncio
from fastapi import APIRouter, WebSocket
from plugins.plugin_comms import ws_reader, ws_writer
from .ies_handler import IES_HANDLER

router = APIRouter()


@router.get("/plugin_ies")
async def check_connection():
    return {"uvicorn": "I Am Alive"}


@router.websocket(
    "/ws/api/v1/plugin/ies/03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4"
)
async def ies_ws(websocket: WebSocket):

    await websocket.accept()
    ies_handler = IES_HANDLER()

    rw = [
        asyncio.create_task(ws_reader(websocket, "ies", ies_handler)),
        asyncio.create_task(
            ws_writer(websocket, "ies"),
        ),
    ]

    try:
        await asyncio.gather(*rw)
    finally:
        [t.cancel() for t in rw]
