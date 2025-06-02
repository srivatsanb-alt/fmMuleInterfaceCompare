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
import app.routers.dependencies as dpd
import utils.log_utils as lu
import utils.util as utils_util
import core.constants as cc
from models.mongo_client import FMMongo
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
    with redis.from_url(os.getenv("FM_REDIS_URI")) as redis_conn:
        body = convert_to_dict(msg)

        body["timestamp"] = time.time()
        body.pop("source")

        if body.get("type", "no_type") == "pass_to_sherpa":
            body.pop("type")
            body.pop("sherpa_name")

        req_id = utils_util.generate_random_job_id()
        body["req_id"] = req_id

        if sherpa.status.disabled_reason == cc.DisabledReason.STALE_HEARTBEAT:
            raise Exception("Sherpa disconnected, cannot send req to sherpa")

        logging.getLogger().info(f"Sending req: {body} to {sherpa.name}")

        sherpa_event: SherpaEvent = SherpaEvent(
            sherpa_name=sherpa.name,
            msg_type=body["endpoint"],
            context="sent to sherpa",
        )
        dbsession.add_to_session(sherpa_event)

        send_ws_msg_to_sherpa(body, sherpa)
        time.sleep(0.005)

        if body["ack_reqd"] is False:
            logging.getLogger().info(f"Ack not reqd for req_id: {req_id}")
            return

        while redis_conn.get(f"success_{req_id}") is None:
            time.sleep(0.005)

        success = json.loads(redis_conn.get(f"success_{req_id}"))
        if success:
            response = json.loads(redis_conn.get(f"response_{req_id}"))
            redis_conn.delete(f"success_{req_id}")
            logging.getLogger().info(f"Response from sherpa {response}")
            return response
        else:
            logging.getLogger().error(f"req id {req_id} failed, req sent: {body}")
            raise Exception(f"Unable to send request to {sherpa.name}")



async def send_async_req_to_sherpa(dbsession, sherpa: Sherpa, msg: FMReq) -> Dict:
    with redis.from_url(os.getenv("FM_REDIS_URI")) as redis_conn:
        body = convert_to_dict(msg)

        body["timestamp"] = time.time()
        body.pop("source")

        if body.get("type", "no_type") == "pass_to_sherpa":
            body.pop("type")
            body.pop("sherpa_name")

        req_id = utils_util.generate_random_job_id()
        body["req_id"] = req_id

        if sherpa.status.disabled_reason == cc.DisabledReason.STALE_HEARTBEAT:
            raise Exception("Sherpa disconnected, cannot send req to sherpa")

        logging.getLogger().info(f"Sending req: {body} to {sherpa.name}")

        send_ws_msg_to_sherpa(body, sherpa)
        await asyncio.sleep(0.005)

        while redis_conn.get(f"success_{req_id}") is None:
            await asyncio.sleep(0.005)

        success = json.loads(redis_conn.get(f"success_{req_id}"))
        if success:
            response = json.loads(redis_conn.get(f"response_{req_id}"))
            redis_conn.delete(f"success_{req_id}")
            logging.getLogger().info(
                f"Response from sherpa {response}, req_id: {req_id} successful"
            )
            return response
        else:
            logging.getLogger().error(f"req id {req_id} failed, req sent: {body}")
            raise Exception(f"Unable to send request to {sherpa.name}")


def send_move_msg(
    dbsession, sherpa: Sherpa, ongoing_trip: OngoingTrip, station: Station
) -> Dict:

    move_msg = MoveReq(
        trip_id=ongoing_trip.trip_id,
        trip_leg_id=ongoing_trip.trip_leg_id,
        destination_pose=station.pose,
        destination_name=station.name,
        basic_trip_description=ongoing_trip.get_basic_trip_description(),
    )
    sherpa.parking_id = None
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
    with redis.from_url(os.getenv("FM_REDIS_URI")) as redis_conn:
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


def send_msg_to_plugin(msg_to_forward, channel_name):
    msg = {
        "msg_to_forward": msg_to_forward,
        "channel_name": channel_name,
        "type": "forward_to_plugin_redis",
    }
    pub = redis.from_url(os.getenv("FM_REDIS_URI"), decode_responses=True)
    pub.publish("channel:plugin_comms", str(msg))


def get_num_units_converyor(conveyor_name):

    with FMMongo() as fm_mongo:
        plugin_info = fm_mongo.get_plugin_info()
        plugin_port = plugin_info["plugin_port"]
        plugin_ip = plugin_info["plugin_ip"]

    plugin_ip = plugin_ip + ":" + plugin_port

    endpoint = os.path.join(
        "http://", plugin_ip, f"plugin/api/v1/conveyor/tote_trip_info/{conveyor_name}"
    )
    logging.getLogger().info(f"Sending request to plugin_conveyor: endpoint: {endpoint}")
    event = threading.Event()
    t = threading.Thread(
        target=cancel_jobs_from_user, args=[f"plugin_conveyor_{conveyor_name}", event]
    )
    t.start()

    username = "fm_to_conveyor"
    user_token = dpd.generate_jwt_token(username)
    kwargs = {"headers": {"X-User-Token": user_token}}
    response = requests.get(endpoint, **kwargs)

    if response.status_code == 200:
        response_json = response.json()
        logging.getLogger().info(f"Got response from plugin conveyor: {response_json}")
    else:
        raise Exception(
            f"Unable to get response from conveyor, response_code: {response.status_code}"
        )

    # close the cancel_jobs_from_user thread
    event.set()
    t.join()

    num_totes = response_json["num_totes"]
    num_trips = response_json["num_trips"]

    if num_trips == 0:
        raise ValueError("num trips cannot be zero. There is an ongoing trip")

    num_units = min(math.ceil(num_totes / num_trips), 2)

    return num_units

def check_response(response):
    response_json = None
    if response.status_code == 200:
        response_json = response.json()
    return response.status_code, response_json

def get_conveyor_url_req_json(endpoint, status=None, tag_name=None, plugin_ip=None):
    if endpoint == "write":
        req_json = [
            {
            "v": f"{status}",
            "id": tag_name        
            }
        ]
        url = f"http://{plugin_ip}/api/v1/conveyor/status/write"
        
        return url, req_json
    elif endpoint == "read":
        url = f"http://{plugin_ip}/api/v1/conveyor/status/read"
        req_json = [tag_name]
        return url, req_json
    elif endpoint == "modbus":
        url = f"http://{plugin_ip}/api/v1/modbus_lift/operation"
        req_json = None
        return url, req_json
    else:
        raise ValueError(f"Invalid endpoint: {endpoint}")
    

def send_req_to_plugin(
    tag_name = None,
    status = None,
    endpoint = None,
    req_type = None,
    req_request_json = None
):
    api_key = None
    with FMMongo() as fm_mongo:
        plugin_info = fm_mongo.get_plugin_info()
        plugin_port = plugin_info["plugin_port"]
        plugin_ip = plugin_info["plugin_ip"]
    
        plugin_conveyor = fm_mongo.get_plugin_conveyor()
        if tag_name and plugin_conveyor:
            tag_name : str = plugin_conveyor[tag_name] if plugin_conveyor.get(tag_name) else None
            api_key = plugin_conveyor["api_key"] if plugin_conveyor.get("api_key") else None

    req_method = getattr(requests, req_type)
    kwargs = {}
    
    
    plugin_ip = plugin_ip + ":" + plugin_port

    url, req_json = get_conveyor_url_req_json(endpoint, status, tag_name, plugin_ip)
    
    if req_request_json:
        req_json = req_request_json


    if api_key:
        kwargs.update({"headers": {"X-API-Key": api_key}})
    else:
        username = "fm_to_plugin"
        user_token = dpd.generate_jwt_token(username)
        kwargs = {"headers": {"X-User-Token": user_token}}

    if req_json:
        kwargs.update({"json": req_json})
    
    args = [url]
    
    response = req_method(*args, **kwargs)
    response_status_code, response_json = check_response(response)

    logging.getLogger().info(
        f"Request to be sent to plugin_conveyor \n url: {url}, method: {req_type} \n body: {req_json}"
    )

    return response_status_code, response_json
