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
import core.handler_configuration as hc
from core.constants import MessageType, WebSocketCloseCode
from models.db_session import DBSession
import models.misc_models as mm
import models.request_models as rqm
import app.routers.dependencies as dpd
import utils.log_utils as lu
import utils.util as utils_util
from utils.rq_utils import Queues, enqueue
import core.common as ccm


MSG_INVALID = "msg_invalid"
MSG_TYPE_REPEATED = "msg_type_repeated_within_time_window"
MSG_TS_INVALID = "msg_timestamp_invalid"
MAX_REJECTS = 3


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
    reject_key = f"{sherpa}_rejects"

    num_rejects = redis.hget(reject_key, msg_type)
    num_rejects = int(num_rejects) if num_rejects else 0

    if num_rejects > MAX_REJECTS:
        logging.getLogger("fm_debug").warning(
            f"Accepting {msg_type} msg from {sherpa}, was rejected: {num_rejects} times"
        )
        num_rejects = redis.hset(reject_key, msg_type, 0)
        return True, None

    # set if not exists
    if not redis.setnx(type_key, ""):
        redis.hset(reject_key, msg_type, num_rejects + 1)
        return False, MSG_TYPE_REPEATED

    # set an expiry of 0.5 seconds
    redis.expire(type_key, expire_after_ms)

    prev_ts = redis.hget(ts_key, msg_type)
    prev_ts = float(prev_ts) if prev_ts else 0.0

    # check if timestamp is valid
    if math.isclose(ts, prev_ts, rel_tol=1e-10) or ts < prev_ts:
        logging.getLogger("fm_debug").warning(
            f"Message rejected: {MSG_TS_INVALID} prev_ts: {prev_ts}, ts: {ts}"
        )
        redis.hset(reject_key, msg_type, num_rejects + 1)
        return False, MSG_TS_INVALID

    redis.hset(ts_key, msg_type, ts)
    redis.hset(reject_key, msg_type, 0)

    return True, None


def freq_ws_req(sherpa_name):
    rkey = f"{sherpa_name}_num_conn_req"
    rkey_ts = f"{sherpa_name}_num_conn_req_ts"
    max_conn = 4
    if redis.setnx(rkey_ts, 1):
        redis.set(rkey, 1)
        rkey_expiry_ms = timedelta(milliseconds=60000)
        redis.expire(rkey_ts, rkey_expiry_ms)
    else:
        num_conn = redis.get(rkey)
        if num_conn is not None:
            num_conn = int(num_conn.decode())
            num_conn += 1
            redis.set(rkey, num_conn)
            if num_conn > max_conn:
                return True
    return False


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

    if freq_ws_req(sherpa_name):
        logger.warning(
            f"Too many websocket connection request from {sherpa_name}, not accepting"
        )
        await websocket.close(
            code=WebSocketCloseCode.RATE_LIMIT_EXCEEDED,
            reason="Too many connection request",
        )
        return

    logger.info(f"websocket connection initiated by {sherpa_name}")
    logger.info(f"websocket connection has to be accepeted for {sherpa_name}")

    with DBSession(engine=ccm.engine) as dbsession:
        sherpa = dbsession.get_sherpa(sherpa_name)
        if sherpa.status.other_info is None:
            sherpa.status.other_info = {}
        manage_sherpa_ip_change(sherpa, x_real_ip)
        connect_notification = f"{sherpa.name} connected to fleet manager!"
        entity_names = [sherpa.fleet.name, sherpa.name]

        # send sherpa connected notification
        log_level = mm.NotificationLevels.info
        module = mm.NotificationModules.generic
        utils_util.maybe_add_notification(
            dbsession, entity_names, connect_notification, log_level, module
        )

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

    logger.info(
        f"websocket connection closed for {sherpa_name}"
    )


async def reader(websocket, sherpa):
    handler_obj = hc.HandlerConfiguration.get_handler()
    sherpa_update_q = Queues.queues_dict[f"{sherpa}_update_handler"]
    sherpa_trip_q = Queues.queues_dict[f"{sherpa}_trip_update_handler"]
    kwargs = {}
    generic_handler_job_timeout = int(
        int(redis.get("generic_handler_job_timeout_ms").decode()) / 1000
    )
    kwargs.update({"ttl": 3})
    kwargs.update({"job_timeout": generic_handler_job_timeout})

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
            logging.getLogger("status_updates").warning(
                f"message rejected type={msg_type},ts={ts},sherpa={sherpa},reason={reason}"
            )
            continue

        if msg_type == MessageType.TRIP_STATUS:
            try:
                msg["source"] = sherpa
                trip_status_msg = rqm.TripStatusMsg.from_dict(msg)
                trip_status_msg.trip_info = rqm.TripInfo.from_dict(msg["trip_info"])
                trip_status_msg.stoppages = rqm.Stoppages.from_dict(msg["stoppages"])
                trip_status_msg.stoppages.extra_info = rqm.StoppageInfo.from_dict(
                    msg["stoppages"]["extra_info"]
                )
                args = [handler_obj, trip_status_msg]
                enqueue(sherpa_trip_q, handle, *args, **kwargs)
            except Exception as e:
                logging.error(f"Unable to enqueue trip status message, Exception: {e}")

        elif msg_type == MessageType.SHERPA_STATUS:
            msg["source"] = sherpa
            if msg.get("current_pose") is None:
                logger.error(
                    f"Ignoring sherpa status from {sherpa}, sherpa pose received as None"
                )
                continue

            if msg.get("sherpa_name") != sherpa:
                temp = msg.get("sherpa_name")
                logger.error(
                    f"sherpa name mismatch, sherpa name in DB: {sherpa}, sherpa_name sent by sherpa: {temp}, will not enqueue sherpa_status msg"
                )
                continue

            try:
                status_msg = rqm.SherpaStatusMsg.from_dict(msg)
                args = [handler_obj, status_msg]
                enqueue(sherpa_update_q, handle, *args, **kwargs)
            except Exception as e:
                logging.getLogger().info(
                    f"Unable to enqueue status msg of type {msg_type} for {sherpa}, exception: {e}"
                )
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
