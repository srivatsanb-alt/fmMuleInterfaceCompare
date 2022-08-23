import ast
import asyncio
import logging
import os
import aioredis
from utils.comms import send_msg_to_frontend
from app.routers.dependencies import get_sherpa, get_frontend_user
from core.config import Config
from core.constants import MessageType
from models.request_models import SherpaStatusMsg, TripStatusMsg
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from models.db_session import session
from utils.rq import Queues, enqueue

router = APIRouter()

@router.websocket("/ws/api/v1/frontend/{token}")
async def sherpa_status(websocket: WebSocket,
                        user_name=Depends(get_frontend_user)):

    if not user_name:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()

    logging.getLogger().info(f"websocket connection started for {user_name}")

    rw = [
        asyncio.create_task(reader(websocket)),
        asyncio.create_task(
            writer(websocket, user),
        ),
    ]
    try:
        await asyncio.gather(*rw)
    except Exception:
        [t.cancel() for t in rw]
    finally:
        [t.cancel() for t in rw]


async def reader(websocket):
    while True:
        try:
            msg = await websocket.receive_json()
        except WebSocketDisconnect:
            logging.info("websocket disconnected")
            return

async def writer(websocket, user):
    redis = aioredis.Redis.from_url(
        os.getenv("FM_REDIS_URI"), max_connections=10, decode_responses=True
    )
    psub = redis.pubsub()
    await psub.subscribe("channel:frontend")
    while True:
        message = await psub.get_message(ignore_subscribe_messages=True, timeout=5)
        if message:
            data = ast.literal_eval(message["data"])
            await websocket.send_json(data)
