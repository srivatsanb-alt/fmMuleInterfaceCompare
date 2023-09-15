import ast
import asyncio
import logging
import logging.config
import os
import aioredis
from fastapi import APIRouter, Depends, WebSocket, status, WebSocketDisconnect


# ati code imports
import app.routers.dependencies as dpd
import utils.log_utils as lu

# setup logging
logging.config.dictConfig(lu.get_log_config_dict())
logger = logging.getLogger("uvicorn")

router = APIRouter()


@router.websocket("/ws/api/v1/plugin_comms/{token}")
async def plugin_comms_ws(
    websocket: WebSocket,
    user_name=Depends(dpd.get_user_from_query),
    x_real_ip=Depends(dpd.get_real_ip_from_header),
):

    client_ip = websocket.client.host
    if x_real_ip is None:
        x_real_ip = client_ip

    if not user_name:
        logger.info(
            f"websocket connection(plugin) request from (ip: {x_real_ip}) will be turned down, Unknown user"
        )
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    logger.info(f"websocket connection(plugin) accepeted client_ip: {x_real_ip}")

    rw = [
        asyncio.create_task(reader(websocket, x_real_ip)),
        asyncio.create_task(
            writer(websocket, x_real_ip),
        ),
    ]
    try:
        await asyncio.gather(*rw)
    except Exception:
        [t.cancel() for t in rw]
    finally:
        [t.cancel() for t in rw]


async def reader(websocket, x_real_ip):
    while True:
        try:
            _ = await websocket.receive_json()
        except WebSocketDisconnect as e:
            logger.info(f"websocket connection(plugin) disconnected client_ip: {x_real_ip}")
            raise e


async def writer(websocket, x_real_ip):
    redis = aioredis.Redis.from_url(
        os.getenv("FM_REDIS_URI"), max_connections=10, decode_responses=True
    )
    psub = redis.pubsub()
    await psub.subscribe("channel:plugin_comms")
    while True:
        message = await psub.get_message(ignore_subscribe_messages=True, timeout=5)
        if message:
            data = ast.literal_eval(message["data"])
            try:
                await websocket.send_json(data)
            except WebSocketDisconnect as e:
                logger.info(
                    f"websocket connection(plugin) disconnected client_ip: {x_real_ip}"
                )
                raise e
