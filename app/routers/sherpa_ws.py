import ast
import asyncio
import logging
import math
import os
from datetime import timedelta
import aioredis
from app.routers.dependencies import (
    get_sherpa,
    get_real_ip_from_header,
)
from models.db_session import DBSession
from core.config import Config
from core.constants import MessageType
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from models.request_models import (
    SherpaStatusMsg,
    TripStatusMsg,
    TripInfo,
    Stoppages,
    StoppageInfo,
)
from sqlalchemy.orm.attributes import flag_modified
from redis import Redis
from utils.rq import Queues, enqueue

redis = Redis.from_url(os.getenv("FM_REDIS_URI"))
router = APIRouter()

MSG_INVALID = "msg_invalid"
MSG_TYPE_REPEATED = "msg_type_repeated_within_time_window"
MSG_TS_INVALID = "msg_timestamp_invalid"

expire_after_ms = timedelta(milliseconds=500)


def manage_sherpa_ip_change(sherpa, x_real_ip):
    if sherpa.ip_address != x_real_ip:
        logging.info(
            f"{sherpa.name} ip has changed since last connection , last_connection_ip: {sherpa.ip_address}"
        )
        sherpa.ip_address = x_real_ip

        try:
            os.remove(
                os.path.join(os.getenv("FM_MAP_DIR"), "certs", f"{sherpa.name}_cert.pem")
            )
            logging.info(f"Removed {sherpa.name} cert file since ip has changed")
        except Exception as e:
            logging.info(f"Unable to remove cert file {e}")
            sherpa.status.other_info.update({"ip_changed": True})
            logging.info(
                f"Updated {sherpa.name} ip address, committed  it the ip change to DB"
            )
    else:
        sherpa.status.other_info.update({"ip_changed": False})
        logging.info(f"{sherpa.name} ip hasn't changed since last connection")

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
    sherpa_name=Depends(get_sherpa),
    x_real_ip=Depends(get_real_ip_from_header),
):
    if not sherpa_name:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    logging.getLogger().info(f"websocket connection initiated by {sherpa_name}")

    # client.host will be nginx container ip
    client_ip = websocket.client.host

    # x_real_ip will be denoting sherpas real ip
    if x_real_ip is None:
        x_real_ip = client_ip

    with DBSession() as dbsession:
        sherpa = dbsession.get_sherpa(sherpa_name)
        if sherpa.status.other_info is None:
            sherpa.status.other_info = {}
        manage_sherpa_ip_change(sherpa, x_real_ip)

    await websocket.accept()

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
            logging.info(f"websocket with {websocket.client.host} disconnected")
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
            # logging.info(f"got a trip status {msg}")
            msg["source"] = sherpa
            trip_status_msg = TripStatusMsg.from_dict(msg)
            trip_status_msg.trip_info = TripInfo.from_dict(msg["trip_info"])
            trip_status_msg.stoppages = Stoppages.from_dict(msg["stoppages"])
            trip_status_msg.stoppages.extra_info = StoppageInfo.from_dict(
                msg["stoppages"]["extra_info"]
            )
            enqueue(sherpa_trip_q, handle, handler_obj, trip_status_msg, ttl=1)

        elif msg_type == MessageType.SHERPA_STATUS:
            msg["source"] = sherpa
            status_msg = SherpaStatusMsg.from_dict(msg)
            enqueue(sherpa_update_q, handle, handler_obj, status_msg, ttl=1)
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
