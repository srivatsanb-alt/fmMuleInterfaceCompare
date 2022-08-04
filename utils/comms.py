from typing import Dict

from core.config import Config
from core.logs import get_logger
from endpoints.request_models import FMCommand
from models.fleet_models import Sherpa


def get_sherpa_url(
    sherpa: Sherpa,
):
    version = Config.get_api_version()
    return f"https://{sherpa.ip_address}/api/{version}/fm"


def post(url, body: Dict):
    # requests.post(url, json=body)
    pass


def send_msg_to_sherpa(sherpa: Sherpa, msg: FMCommand):
    base_url = get_sherpa_url(sherpa)
    body = msg.dict()
    endpoint = body.pop("endpoint")
    url = f"{base_url}/{endpoint}"
    post(url, body)
    get_logger(sherpa.name).info(f"msg to {sherpa.name}: {body}")
    get_logger(sherpa.name).info(f"msg url: {url}")
