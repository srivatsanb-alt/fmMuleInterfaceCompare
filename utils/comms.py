import time
from typing import Dict

import requests

from core.config import Config
from core.logs import get_logger
from endpoints.request_models import FMReq
from models.fleet_models import Sherpa


def get_sherpa_url(
    sherpa: Sherpa,
):
    version = Config.get_api_version()
    port = Config.get_sherpa_port()
    return f"https://{sherpa.ip_address}:{port}/api/{version}/fm"


def post(url, body: Dict):
    # from unittest.mock import Mock
    # from requests.models import Response
    # import json

    # response = Mock(spec=Response)

    # resp_d = {
    # "display_name": "S2",
    # "hwid": "abcd",
    # "ip_address": "10.4.5.6",
    # "map_files_match": True,
    # }
    # response.json.return_value = json.dumps(resp_d)
    # response.status_code = 200
    #
    # return response

    return requests.post(url, json=body)


def send_msg_to_sherpa(sherpa: Sherpa, msg: FMReq):
    body = msg.dict()
    body["timestamp"] = time.time()
    endpoint = body.pop("endpoint")

    base_url = get_sherpa_url(sherpa)
    url = f"{base_url}/{endpoint}"

    get_logger(sherpa.name).info(f"msg to {sherpa.name}: {body}")
    get_logger(sherpa.name).info(f"msg url: {url}")
    return post(url, body)


def process_response(response: requests.Response):
    response.raise_for_status()
    return response.json()
