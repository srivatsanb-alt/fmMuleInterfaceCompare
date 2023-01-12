import os
import time
from typing import Dict
import redis
import math
import requests
import threading
import json
from rq.job import Job


from core.config import Config
from core.logs import get_logger
from models.fleet_models import SherpaEvent
from models.fleet_models import Sherpa, Station
from models.request_models import FMReq, MoveReq
from models.trip_models import OngoingTrip


def get_sherpa_url(
    sherpa: Sherpa,
):
    version = Config.get_api_version()
    port = sherpa.port if sherpa.port else Config.get_sherpa_port()
    scheme = Config.get_http_scheme() if Config.get_http_scheme() else "http"
    verify = False
    if scheme == "https":
        port = 443
        verify = os.path.join(os.getenv("FM_MAP_DIR"), "certs", f"{sherpa.name}_cert.pem")

    return f"{scheme}://{sherpa.ip_address}:{port}/api/{version}/fm", verify


def post(url, verify, body: Dict, sherpa: Sherpa) -> Dict:
    response = requests.post(url, verify=verify, json=body)
    return process_response(response, url, body, sherpa)


def get(sherpa: Sherpa, req: FMReq) -> Dict:
    base_url, verify = get_sherpa_url(sherpa)
    url = f"{base_url}/{req.endpoint}"
    response = requests.get(url, verify=verify)
    return process_response(response, url, req, sherpa)


def send_msg_to_sherpa(dbsession, sherpa: Sherpa, msg: FMReq) -> Dict:

    body = msg.dict()
    body["timestamp"] = time.time()
    endpoint = body.pop("endpoint")

    if body.get("type", "no_type") == "pass_to_sherpa":
        body.pop("type")
        body.pop("sherpa_name")

    base_url, verify = get_sherpa_url(sherpa)
    url = f"{base_url}/{endpoint}"

    get_logger().info(f"Sending msg to {sherpa.name}")
    get_logger(sherpa.name).info(f"msg to {sherpa.name}: {body}, {url}")

    sherpa_event: SherpaEvent = SherpaEvent(
        sherpa_name=sherpa.name,
        msg_type=endpoint,
        context="sent to sherpa",
    )
    dbsession.add_to_session(sherpa_event)

    return post(url, verify, body, sherpa)


def process_response(
    response: requests.Response,
    url,
    req=None,
    sherpa=None,
) -> Dict:

    response.raise_for_status()
    if sherpa:
        get_logger().info(
            f"sherpa_name: {sherpa.name} || sherpa_ip: {sherpa.ip_address}:{sherpa.port} \n url: {url} \n Request_to_{sherpa.name}: {req} \n Response_from_{sherpa.name}: {response.json()}\n"
        )

    else:
        get_logger().info(f"url: {url} \n Request: {req} \n Response: {response.json()}\n")

    return response


def send_move_msg(
    dbsession, sherpa: Sherpa, ongoing_trip: OngoingTrip, station: Station
) -> Dict:
    move_msg = MoveReq(
        trip_id=ongoing_trip.trip_id,
        trip_leg_id=ongoing_trip.trip_leg_id,
        destination_pose=station.pose,
        destination_name=station.name,
    )
    return send_msg_to_sherpa(dbsession, sherpa, move_msg)


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
        "http://", plugin_ip, f"/plugin/conveyor/tote_trip_info/{conveyor_name}"
    )

    event = threading.Event()

    t = threading.Thread(
        target=cancel_jobs_from_user, args=[f"plugin_conveyor_{conveyor_name}", event]
    )
    t.start()

    response = requests.get(endpoint)

    # close the cancel_jobs_from_user thread
    event.set()
    t.join()

    num_units = min(math.ceil(response["num_totes"] / response["num_trips"]), 2)

    return num_units
