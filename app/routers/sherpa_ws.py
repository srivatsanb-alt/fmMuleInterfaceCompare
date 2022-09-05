import ast
import asyncio
import logging
import os

import aioredis
from app.routers.dependencies import get_db_session, get_sherpa
from core.config import Config
from core.constants import MessageType
from models.request_models import SherpaStatusMsg, TripStatusMsg
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from utils.rq import Queues, enqueue
from utils.comms import send_status_update

router = APIRouter()


@router.websocket("/ws/api/v1/sherpa/")
async def sherpa_status(
    websocket: WebSocket, sherpa=Depends(get_sherpa), session=Depends(get_db_session)
):
    if not sherpa:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    logging.getLogger().info(f"websocket connection started for {sherpa}")

    client_ip = websocket.client.host
    db_sherpa = session.get_sherpa(sherpa)
    if db_sherpa.ip_address != client_ip:
        # write IP address to sherpa table
        db_sherpa.ip_address = client_ip

    rw = [
        asyncio.create_task(reader(websocket, sherpa)),
        asyncio.create_task(
            writer(websocket, sherpa),
        ),
    ]
    try:
        await asyncio.gather(*rw)
    except Exception:
        [t.cancel() for t in rw]
    finally:
        [t.cancel() for t in rw]


async def reader(websocket, sherpa):
    handler_obj = Config.get_handler()
    while True:
        try:
            msg = await websocket.receive_json()
        except WebSocketDisconnect:
            logging.info("websocket disconnected")
            return

        msg_type = msg.get("type")

        if msg_type == MessageType.TRIP_STATUS:
            send_status_update(msg)
            msg["source"] = sherpa
            trip_status_msg = TripStatusMsg.from_dict(msg)
            enqueue(Queues.handler_queue, handle, handler_obj, trip_status_msg, ttl=2)
        elif msg_type == MessageType.SHERPA_STATUS:
            msg["source"] = sherpa
            status_msg = SherpaStatusMsg.from_dict(msg)
            enqueue(Queues.handler_queue, handle, handler_obj, status_msg)
        else:
            logging.getLogger().error(f"Unsupported message type {msg_type}")


async def writer(websocket, sherpa):
    redis = aioredis.Redis.from_url(
        os.getenv("FM_REDIS_URI"), max_connections=10, decode_responses=True
    )
    psub = redis.pubsub()
    await psub.subscribe(f"channel:{sherpa}")

    while True:
        message = await psub.get_message(ignore_subscribe_messages=True, timeout=5)
        if message:
            data = ast.literal_eval(message["data"])
            await websocket.send_json(data)


def handle(handler, msg):
    handler.handle(msg)
