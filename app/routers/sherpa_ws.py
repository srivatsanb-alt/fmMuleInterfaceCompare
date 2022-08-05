import ast
import asyncio
import logging
import os
import aioredis
from fastapi import APIRouter, Depends, WebSocket

from app.routers.dependencies import get_sherpa
from core.config import Config
from core.constants import MessageType
from endpoints.request_models import SherpaStatusMsg
from utils.rq import Queues, enqueue

router = APIRouter()


@router.websocket("/api/v1/sherpa/")
async def status(websocket: WebSocket, sherpa: str = Depends(get_sherpa)):
    if not sherpa:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    logging.getLogger().info(f"websocket connection started for {sherpa}")

    rw = [
        asyncio.create_task(reader(websocket)),
        asyncio.create_task(
            writer(websocket, sherpa),
        ),
    ]
    try:
        await asyncio.gather(*rw)
    finally:
        [t.cancel() for t in rw]


async def reader(websocket):
    handler_obj = Config.get_handler()
    while True:
        msg = await websocket.receive_json()
        msg_type = msg.get("type")
        if msg_type == MessageType.TRIP_STATUS:
            enqueue(Queues.handler_queue, handle, handler_obj, msg, ttl=2)
        elif msg_type == MessageType.SHERPA_STATUS:
            status_msg = SherpaStatusMsg.from_dict(msg)
            enqueue(Queues.handler_queue, handle, handler_obj, status_msg)
        else:
            logging.getLogger().error(f"Unsupported message type {msg_type}")


async def writer(websocket, sherpa):
    redis = aioredis.Redis.from_url(
        os.getenv("HIVEMIND_REDIS_URI"), max_connections=10, decode_responses=True
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
