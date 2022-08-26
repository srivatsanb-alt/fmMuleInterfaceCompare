import ast
import asyncio
import logging
import os
import json

import aioredis
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status

from app.routers.dependencies import get_user_from_query

router = APIRouter()


@router.websocket("/ws/api/v1/updates/{token}")
async def sherpa_status(websocket: WebSocket,
                        user_name=Depends(get_user_from_query)):

    if not user_name:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()

    logging.getLogger().info(f"websocket connection started for {user_name}")

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
        try:
            msg = await websocket.receive_json()
        except WebSocketDisconnect:
            logging.info("websocket disconnected")
            return


async def writer(websocket):
    redis = aioredis.Redis.from_url(
        os.getenv("FM_REDIS_URI"), max_connections=10, decode_responses=True
    )
    psub = redis.pubsub()
    await psub.subscribe("channel:status_updates")
    while True:
        message = await psub.get_message(ignore_subscribe_messages=True, timeout=5)
        if message:
            try:
                data = ast.literal_eval(message["data"])
                await websocket.send_json(data)
            except Exception as e:
                pass
                #logging.info(f"unable to send a websocket update, exception {e}")
