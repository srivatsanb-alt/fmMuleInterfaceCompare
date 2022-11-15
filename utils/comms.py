import os
import time
from typing import Dict
import redis
from models.db_session import session
from models.fleet_models import SherpaEvent
import requests
from core.config import Config
from core.logs import get_logger
from models.fleet_models import Sherpa, Station
from models.request_models import FMReq, MoveReq
from models.trip_models import OngoingTrip


redis_db = redis.from_url(os.getenv("FM_REDIS_URI"))


def get_sherpa_url(
    sherpa: Sherpa,
):
    version = Config.get_api_version()
    port = sherpa.port if sherpa.port else Config.get_sherpa_port()
    return f"http://{sherpa.ip_address}:{port}/api/{version}/fm"


def post(url, body: Dict, sherpa: Sherpa) -> Dict:
    response = requests.post(url, json=body)
    return process_response(response, url, body, sherpa)


def get(sherpa: Sherpa, req: FMReq) -> Dict:
    base_url = get_sherpa_url(sherpa)
    url = f"{base_url}/{req.endpoint}"
    response = requests.get(url)
    return process_response(response, url, req, sherpa)


def send_msg_to_sherpa(sherpa: Sherpa, msg: FMReq) -> Dict:

    body = msg.dict()
    body["timestamp"] = time.time()
    endpoint = body.pop("endpoint")

    if body.get("type", "no_type") == "pass_to_sherpa":
        body.pop("type")
        body.pop("sherpa_name")

    base_url = get_sherpa_url(sherpa)
    url = f"{base_url}/{endpoint}"

    get_logger().info(f"Sending msg to {sherpa.name}")
    get_logger(sherpa.name).info(f"msg to {sherpa.name}: {body}, {url}")

    sherpa_event: SherpaEvent = SherpaEvent(
        sherpa_name=sherpa.name,
        msg_type=endpoint,
        context="sent to sherpa",
    )
    session.add_to_session(sherpa_event)

    return post(url, body, sherpa)


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


def send_move_msg(sherpa: Sherpa, ongoing_trip: OngoingTrip, station: Station) -> Dict:
    move_msg = MoveReq(
        trip_id=ongoing_trip.trip_id,
        trip_leg_id=ongoing_trip.trip_leg_id,
        destination_pose=station.pose,
        destination_name=station.name,
    )
    return send_msg_to_sherpa(sherpa, move_msg)


def send_status_update(msg):
    pub = redis.from_url(os.getenv("FM_REDIS_URI"), decode_responses=True)
    pub.publish("channel:status_updates", str(msg))
