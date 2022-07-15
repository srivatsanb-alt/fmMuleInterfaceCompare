import ast
import os
import aioredis
import asyncio
import logging
from fastapi import APIRouter, Depends
from rq.queue import Queue
from hivemind import core, models
import logging
import hashlib
from fastapi import APIRouter, Depends, Header, WebSocket, status
from sqlalchemy.orm import Session
from typing import Optional


from hivemind.fleet_manager.logs import get_logger
from hivemind.core.db import get_redis

#import connection handlers
from connections.ies import handle_ies_msgs
from hivemind.fleet_manager.workers import ies_handler_queue, enqueue

unauthenticated_router = APIRouter()

def get_client(
    client_api_key: Optional[str] = Header(None),
    db: Session = Depends(core.get_db),
):

    if client_api_key is None:
        return None

    hashed_api_key = hashlib.sha256(client_api_key.encode("utf-8")).hexdigest()
    client = (
         db.query(models.Clients)
        .filter(models.Clients.hashed_api_key == hashed_api_key)
        .one_or_none()
    )

    return client


@unauthenticated_router.websocket("/rt/external/")
async def websocket_endpoint(
            websocket: WebSocket,
            client: str = Depends(get_client)
            ):

    if client is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()
    rw = [
        asyncio.create_task(
            reader(websocket, client.name, handle_connection_msgs)
            ),
        asyncio.create_task(
            writer(websocket, client.name),
        )
    ]

    try:
        await asyncio.gather(*rw)
    finally:
        [t.cancel() for t in rw]


async def reader(websocket, client_name, func_handle):
    logging.info(f"reading from_client {client_name}")
    connection_queue = Queue("from_external_" + client_name , connection = get_redis())
    while True:
        data = await websocket.receive_json()
        data["name"] = client_name
        asyncio.get_running_loop().run_in_executor(
            None, enqueue, connection_queue, func_handle , data
        )

async def writer(websocket, client_name):
    logging.info(f"writing to client {client_name}")

    redis = aioredis.Redis.from_url(
        os.getenv("HIVEMIND_REDIS_URI"), max_connections = 10, decode_responses = True
    )
    psub = redis.pubsub()
    await psub.subscribe(f"channel:external_{client_name}")
    logging.info(f"subscribed to channel: external_{client_name}")

    while True:
        message = await psub.get_message(ignore_subscribe_messages = True, timeout = 0.5)
        if message is not None:
            data = ast.literal_eval(message["data"])
            await websocket.send_json(data)
            logging.debug(f"to client {client_name}: {data}")
        await asyncio.sleep(0.05)


def handle_connection_msgs(msg):
    if msg["name"] == "ies":
        get_logger().debug(f"from IES: {msg}")
        enqueue(ies_handler_queue, handle_ies_msgs, msg)
