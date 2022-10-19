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


def post_mock(url, body: Dict) -> Dict:
    return process_response_mock(None)


def post(url, body: Dict) -> Dict:
    response = requests.post(url, json=body)
    return process_response(response, body)


def get_mock(sherpa: Sherpa, req: FMReq) -> Dict:
    return process_response_mock(None, json=True)


def get(sherpa: Sherpa, req: FMReq) -> Dict:
    base_url = get_sherpa_url(sherpa)
    url = f"{base_url}/{req.endpoint}"
    response = requests.get(url)
    return process_response(response, req)


def send_msg_to_sherpa(sherpa: Sherpa, msg: FMReq) -> Dict:

    body = msg.dict()
    body["timestamp"] = time.time()
    endpoint = body.pop("endpoint")

    if body.get("type", "no_type") == "pass_to_sherpa":
        body.pop("type")
        body.pop("sherpa_name")

    base_url = get_sherpa_url(sherpa)
    url = f"{base_url}/{endpoint}"

    get_logger(sherpa.name).info(f"msg to {sherpa.name}: {body}")
    get_logger(sherpa.name).info(f"msg url: {url}")

    sherpa_event: SherpaEvent = SherpaEvent(
        sherpa_name=sherpa.name,
        msg_type=endpoint,
        context="sent to sherpa",
    )
    session.add_to_session(sherpa_event)

    return post(url, body)


def process_response_mock(response: requests.Response, json=False) -> Dict:
    from unittest.mock import Mock

    from requests.models import Response

    response = Mock(spec=Response)

    resp_d = {
        "display_name": "S2",
        "hwid": "abcd",
    }
    if json:
        response.json.return_value = resp_d
    response.status_code = 200

    return response


def process_response(response: requests.Response, req=None) -> Dict:
    response.raise_for_status()
    get_logger().info(f"received response: {response.json()}, Request: {req}")
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
