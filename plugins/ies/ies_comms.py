import asyncio
from fastapi import APIRouter, WebSocket, Depends
from plugins.plugin_comms import ws_reader, ws_writer
from .ies_handler import IES_HANDLER
import plugins.ies.ies_request_models as irqm
import app.routers.dependencies as dpd
from plugins.plugin_rq import enqueue, get_job_result, get_redis_conn
from rq import Queue

router = APIRouter()


@router.get("/plugin_ies")
async def check_connection():
    return {"uvicorn": "I Am Alive"}


@router.post("/plugin/ies/add_ies_station")
async def add_ies_station(
    info: irqm.IesStation, user_name=Depends(dpd.get_user_from_header)
):
    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    response = {}
    q = Queue("plugin_ies", connection=get_redis_conn())
    ies_handler = IES_HANDLER()
    msg = {
        "messageType": "add_ies_station",
        "ati_name": info.ati_name,
        "ies_name": info.ies_name,
    }
    job = enqueue(q, ies_handler.handle, msg)
    response = await get_job_result(job.id)
    return {}


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
