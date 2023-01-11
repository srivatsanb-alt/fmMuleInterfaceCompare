import ast
import asyncio
import logging
import logging.config
import os
import aioredis
from fastapi import APIRouter, Depends, WebSocket, status

from app.routers.dependencies import get_user_from_query

# setup logging
log_conf_path = os.path.join(os.getenv("FM_CONFIG_DIR"), "logging.conf")
logging.config.fileConfig(log_conf_path)
logger = logging.getLogger("uvicorn")

router = APIRouter()


@router.websocket("/ws/api/v1/updates/{token}")
async def update_ws(websocket: WebSocket, user_name=Depends(get_user_from_query)):

    if not user_name:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()

    logger.info(f"websocket connection started for {user_name}")

    rw = [
        asyncio.create_task(reader(websocket)),
        asyncio.create_task(
            writer(websocket),
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
        _ = await websocket.receive_json()


async def writer(websocket):
    redis = aioredis.Redis.from_url(
        os.getenv("FM_REDIS_URI"), max_connections=10, decode_responses=True
    )
    psub = redis.pubsub()
    await psub.subscribe("channel:status_updates")
    while True:
        message = await psub.get_message(ignore_subscribe_messages=True, timeout=5)
        if message:
            data = ast.literal_eval(message["data"])
            await websocket.send_json(data)
