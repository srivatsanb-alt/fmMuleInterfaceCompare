import logging
import logging.config
import os
import time
from typing import Dict
import redis
import math
import requests
import threading
import json
from enum import Enum
from rq.job import Job
from pydantic import BaseModel
import asyncio

# ati code imports
import utils.log_utils as lu
import utils.util as utils_util
import core.constants as cc
from models.fleet_models import SherpaEvent
from models.fleet_models import Sherpa, Station
from models.request_models import FMReq, MoveReq
from models.trip_models import OngoingTrip


logging.config.dictConfig(lu.get_log_config_dict())


def convert_to_dict(msg):
    if isinstance(msg, BaseModel):
        body = msg.dict()
    elif isinstance(msg, dict):
        body = msg
    else:
        raise Exception("Cannot convert to dict")

    for key, val in body.items():
        if isinstance(val, BaseModel):
            body[key] = convert_to_dict(val)
        if isinstance(val, Enum):
            body[key] = str(val.value)
        if isinstance(val, dict):
            body[key] = convert_to_dict(val)

    return body


# utility for communication between sherpa and fleet manager
def send_req_to_sherpa(dbsession, sherpa: Sherpa, msg: FMReq) -> Dict:
    redis_conn = redis.from_url(os.getenv("FM_REDIS_URI"))

    body = convert_to_dict(msg)

    body["timestamp"] = time.time()
    body.pop("source")

    if body.get("type", "no_type") == "pass_to_sherpa":
        body.pop("type")
        body.pop("sherpa_name")

    req_id = utils_util.generate_random_job_id()
    body["req_id"] = req_id

    if sherpa.status.disabled_reason == cc.DisabledReason.STALE_HEARTBEAT:
        raise ValueError("Sherpa disconnected, cannot send req to sherpa")

    logging.getLogger().info(f"Sending req: {body} to {sherpa.name}")

    sherpa_event: SherpaEvent = SherpaEvent(
        sherpa_name=sherpa.name,
        msg_type=body["endpoint"],
        context="sent to sherpa",
    )
    dbsession.add_to_session(sherpa_event)

    send_ws_msg_to_sherpa(body, sherpa)
    time.sleep(0.005)

    while redis_conn.get(f"success_{req_id}") is None:
        time.sleep(0.005)

    success = json.loads(redis_conn.get(f"success_{req_id}"))
    if success:
        response = json.loads(redis_conn.get(f"response_{req_id}"))
        redis_conn.delete(f"success_{req_id}")
        logging.getLogger().info(f"Response from sherpa {response}")
        return response
    else:
        raise Exception(f"req id {req_id} failed, req sent: {body}")


async def send_async_req_to_sherpa(dbsession, sherpa: Sherpa, msg: FMReq) -> Dict:
    redis_conn = redis.from_url(os.getenv("FM_REDIS_URI"))

    body = convert_to_dict(msg)

    body["timestamp"] = time.time()
    body.pop("source")

    if body.get("type", "no_type") == "pass_to_sherpa":
        body.pop("type")
        body.pop("sherpa_name")

    req_id = utils_util.generate_random_job_id()
    body["req_id"] = req_id

    if sherpa.status.disabled_reason == cc.DisabledReason.STALE_HEARTBEAT:
        raise ValueError("Sherpa disconnected, cannot send req to sherpa")

    logging.getLogger().info(f"Sending req: {body} to {sherpa.name}")

    send_ws_msg_to_sherpa(body, sherpa)
    await asyncio.sleep(0.005)

    while redis_conn.get(f"success_{req_id}") is None:
        await asyncio.sleep(0.005)

    success = json.loads(redis_conn.get(f"success_{req_id}"))
    if success:
        response = json.loads(redis_conn.get(f"response_{req_id}"))
        redis_conn.delete(f"success_{req_id}")
        logging.getLogger().info(f"Response from sherpa {response}")
        return response
    else:
        raise Exception(f"req id {req_id} failed, req sent: {body}")


def send_move_msg(
    dbsession, sherpa: Sherpa, ongoing_trip: OngoingTrip, station: Station
) -> Dict:
    move_msg = MoveReq(
        trip_id=ongoing_trip.trip_id,
        trip_leg_id=ongoing_trip.trip_leg_id,
        destination_pose=station.pose,
        destination_name=station.name,
    )
    return send_req_to_sherpa(dbsession, sherpa, move_msg)


def send_status_update(msg):
    pub = redis.from_url(os.getenv("FM_REDIS_URI"), decode_responses=True)
    pub.publish("channel:status_updates", str(msg))


def send_ws_msg_to_sherpa(msg, sherpa):
    pub = redis.from_url(os.getenv("FM_REDIS_URI"), decode_responses=True)
    pub.publish(f"channel:{sherpa.name}", str(msg))


def send_notification(msg):
    pub = redis.from_url(os.getenv("FM_REDIS_URI"), decode_responses=True)
    pub.publish("channel:notifications", str(msg))


def close_websocket_for_sherpa(sherpa_name):
    msg = {"close_ws": True}
    pub = redis.from_url(os.getenv("FM_REDIS_URI"), decode_responses=True)
    pub.publish(f"channel:{sherpa_name}", str(msg))


# conveyor related comms
def cancel_jobs_from_user(user, event):
    redis_conn = redis.from_url(os.getenv("FM_REDIS_URI"))
    while True:
        if event.is_set():
            break
        queued_jobs = redis_conn.get("queued_jobs")
        if queued_jobs is None:
            queued_jobs = b"{}"
        queued_jobs = json.loads(queued_jobs)

        jobs_source = queued_jobs.get(user)
        if jobs_source is None:
            jobs_source = []

        for job_id in jobs_source:
            logging.getLogger().info(f"Will cancel job(id:{job_id} from {user})")
            job = Job.fetch(job_id, connection=redis_conn)
            job.cancel()

        time.sleep(0.05)


def send_msg_to_conveyor(msg, conveyor_name):
    pub = redis.from_url(os.getenv("FM_REDIS_URI"), decode_responses=True)
    pub.publish(f"channel:plugin_conveyor_{conveyor_name}", str(msg))


def get_num_units_converyor(conveyor_name):
    plugin_port = os.getenv("PLUGIN_PORT")
    plugin_ip = "127.0.0.1"
    plugin_ip = plugin_ip + ":" + plugin_port
    endpoint = os.path.join(
        "http://", plugin_ip, f"plugin/conveyor/tote_trip_info/{conveyor_name}"
    )

    event = threading.Event()

    t = threading.Thread(
        target=cancel_jobs_from_user, args=[f"plugin_conveyor_{conveyor_name}", event]
    )
    t.start()

    response = requests.get(endpoint)

    if response.status_code == 200:
        response_json = response.json()

    # close the cancel_jobs_from_user thread
    event.set()
    t.join()

    num_totes = response_json["num_totes"]
    num_trips = response_json["num_trips"]

    if num_trips == 0:
        raise ValueError("num trips cannot be zero. There is an ongoing trip")

    num_units = min(math.ceil(num_totes / num_trips), 2)

    return num_units
