import ast
import asyncio
import logging
import logging.config
import math
import os
from datetime import timedelta
import aioredis
from sqlalchemy.orm.attributes import flag_modified
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from redis import Redis


# ati code imports
from core.config import Config
from core.constants import MessageType
from models.db_session import DBSession
import models.request_models as rqm
import app.routers.dependencies as dpd
import utils.log_utils as lu
from utils.rq_utils import Queues, enqueue

MSG_INVALID = "msg_invalid"
MSG_TYPE_REPEATED = "msg_type_repeated_within_time_window"
MSG_TS_INVALID = "msg_timestamp_invalid"


# setup logging
logging.config.dictConfig(lu.get_log_config_dict())
logger = logging.getLogger("uvicorn")


redis = Redis.from_url(os.getenv("FM_REDIS_URI"))
router = APIRouter()


expire_after_ms = timedelta(milliseconds=500)
# performs status updates at regular intervals, read, write,
# websocket messages and manages websocket connection between sherpas and FM.


def manage_sherpa_ip_change(sherpa, x_real_ip):
    if sherpa.ip_address != x_real_ip:
        logger.info(
            f"{sherpa.name} ip has changed since last connection , last_connection_ip: {sherpa.ip_address}"
        )

        sherpa.ip_address = x_real_ip
        sherpa.port = None
        sherpa.status.other_info.update({"ip_changed": True})
    else:
        sherpa.status.other_info.update({"ip_changed": False})
        logger.info(f"{sherpa.name} ip hasn't changed since last connection")

    flag_modified(sherpa.status, "other_info")


def accept_message(sherpa: str, msg):
    msg_type = msg.get("type")
    ts = msg.get("timestamp")

    if not msg_type or not ts:
        return False, MSG_INVALID

    type_key = f"{sherpa}_{msg_type}"
    ts_key = f"{sherpa}_ts"

    if not redis.setnx(type_key, ""):
        # same message type received less than 0.5 seconds ago
        return False, MSG_TYPE_REPEATED
    # set an expiry of 0.5 seconds
    redis.expire(type_key, expire_after_ms)

    prev_ts = redis.hget(ts_key, msg_type)
    prev_ts = float(prev_ts) if prev_ts else 0.0

    # check if timestamp is valid
    if math.isclose(ts, prev_ts, rel_tol=1e-10) or ts < prev_ts:
        return False, MSG_TS_INVALID

    redis.hset(ts_key, msg_type, ts)
    return True, None


@router.websocket("/ws/api/v1/sherpa/")
async def sherpa_status(
    websocket: WebSocket,
    sherpa_name=Depends(dpd.get_sherpa),
    x_real_ip=Depends(dpd.get_real_ip_from_header),
):

    client_ip = websocket.client.host
    if x_real_ip is None:
        x_real_ip = client_ip

    if not sherpa_name:
        logger.info(
            f"websocket connection initiated with an invalid api_key or sherpa has not been added to DB. WS request came from ip: {x_real_ip}"
        )
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    logger.info(f"websocket connection initiated by {sherpa_name}")
    logger.info(f"websocket connection has to be accepeted for {sherpa_name}")

    with DBSession() as dbsession:
        sherpa = dbsession.get_sherpa(sherpa_name)
        if sherpa.status.other_info is None:
            sherpa.status.other_info = {}
        manage_sherpa_ip_change(sherpa, x_real_ip)

    await websocket.accept()
    logger.info(f"websocket connection accepeted for {sherpa_name}")

    rw = [
        asyncio.create_task(reader(websocket, sherpa_name)),
        asyncio.create_task(
            writer(websocket, sherpa_name),
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
        except WebSocketDisconnect as e:
            logger.info(f"websocket connection with {sherpa} disconnected")
            raise e

        msg_type = msg.get("type")
        ts = msg.get("timestamp")

        ok, reason = accept_message(sherpa, msg)
        if not ok:
            logging.warn(
                f"message rejected type={msg_type},ts={ts},sherpa={sherpa},reason={reason}"
            )
            continue

        sherpa_update_q = Queues.queues_dict[f"{sherpa}_update_handler"]
        sherpa_trip_q = Queues.queues_dict[f"{sherpa}_trip_update_handler"]

        if msg_type == MessageType.TRIP_STATUS:
            msg["source"] = sherpa
            trip_status_msg = rqm.TripStatusMsg.from_dict(msg)
            trip_status_msg.trip_info = rqm.TripInfo.from_dict(msg["trip_info"])
            trip_status_msg.stoppages = rqm.Stoppages.from_dict(msg["stoppages"])
            trip_status_msg.stoppages.extra_info = rqm.StoppageInfo.from_dict(
                msg["stoppages"]["extra_info"]
            )
            enqueue(sherpa_trip_q, handle, handler_obj, trip_status_msg, ttl=1)

        elif msg_type == MessageType.SHERPA_STATUS:
            msg["source"] = sherpa
            status_msg = rqm.SherpaStatusMsg.from_dict(msg)
            if status_msg.sherpa_name != sherpa:
                logger.error(
                    f"sherpa name mismatch, sherpa name in DB: {sherpa}, sherpa_name sent by sherpa: {temp}, will not enqueue sherpa_status msg"
                )
            else:
                enqueue(sherpa_update_q, handle, handler_obj, status_msg, ttl=1)
        else:
            logging.error(f"Unsupported message type {msg_type}")

        await asyncio.sleep(0.01)


async def writer(websocket, sherpa):
    redis = aioredis.Redis.from_url(
        os.getenv("FM_REDIS_URI"), max_connections=10, decode_responses=True
    )
    psub = redis.pubsub()
    await psub.subscribe(f"channel:{sherpa}")

    while True:
        message = await psub.get_message(ignore_subscribe_messages=True, timeout=0.5)
        if message:
            data = ast.literal_eval(message["data"])

            # close WebSocket message
            if data.get("close_ws", False):
                await websocket.close()

            try:
                await websocket.send_json(data)
            except WebSocketDisconnect as e:
                logger.error(f"websocket connection with {sherpa} disconnected")
                raise e

        await asyncio.sleep(0.01)


def handle(handler, msg, **kwargs):
    handler.handle(msg)
