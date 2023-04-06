import logging
import os
import requests
from dataclasses import dataclass
import toml


@dataclass
class MFMContext:
    http_scheme: str
    x_api_key: str
    server_ip: str
    server_port: str
    ws_scheme: str
    ws_suffix: str
    cert_file: str
    update_freq: int
    ws_update_freq: int


def get_mfm_ws_url(mfm_context: MFMContext):
    mfm_ws_prefix = (
        mfm_context.ws_scheme
        + "://"
        + mfm_context.server_ip
        + ":"
        + mfm_context.server_port
    )
    return os.path.join(mfm_ws_prefix, mfm_context.ws_suffix)


def get_mfm_url(mfm_context: MFMContext, endpoint, query=""):
    mfm_url = (
        mfm_context.http_scheme
        + "://"
        + mfm_context.server_ip
        + ":"
        + mfm_context.server_port
    )
    fm_endpoints = {
        "update_fleet_info": os.path.join(
            mfm_url, "api/v1/master_fm/fm_client/update_fleet_info"
        ),
        "update_sherpa_info": os.path.join(
            mfm_url, "api/v1/master_fm/fm_client/update_sherpa_info"
        ),
        "upload_map_files": os.path.join(
            mfm_url, "api/v1/master_fm/fm_client/upload_map_files", str(query)
        ),
        "update_trip_info": os.path.join(
            mfm_url, "api/v1/master_fm/fm_client/update_trip_info"
        ),
        "update_trip_analytics": os.path.join(
            mfm_url, "api/v1/master_fm/fm_client/update_trip_analytics"
        ),
    }
    return fm_endpoints.get(endpoint, None)


def check_response(response):
    response_json = None
    if response.status_code == 200:
        response_json = response.json()
    return response.status_code, response_json


def send_http_req_to_mfm(
    mfm_context, endpoint, req_type, req_json=None, files=None, query=""
):
    response_json = None
    url = get_mfm_url(mfm_context, endpoint, query)

    req_method = getattr(requests, req_type)
    args = [url]
    kwargs = {"headers": {"X-API-Key": mfm_context.x_api_key}}

    if req_json:
        kwargs.update({"json": req_json})

    if files:
        kwargs.update({"files": files})

    if mfm_context.http_scheme == "https":
        kwargs.update({"verify": mfm_context.cert_file})

    logging.getLogger("mfm_updates").info(
        f"will send http req to {url}, req_json: {req_json}, files: {files}"
    )

    try:
        response = req_method(*args, **kwargs)
        response_status_code, response_json = check_response(response)
    except Exception as e:
        logging.getLogger("mfm_updates").info(
            f"unable to send http req to {url}, req_json: {req_json}, files: {files}, exception: {e}"
        )
        response_status_code = 400

    return response_status_code, response_json


def get_mfm_context():
    mfm_config_path = os.path.join(os.getenv("FM_CONFIG_DIR"), "master_fm_config.toml")

    if not os.path.exists(mfm_config_path):
        logging.getLogger("mfm_updates").error(f"mfm_config : {mfm_config_path} not found")
        return

    mfm_config = toml.load(mfm_config_path)

    mfm_context = MFMContext(
        http_scheme=mfm_config["master_fm"]["http_scheme"],
        server_ip=mfm_config["master_fm"]["mfm_ip"],
        server_port=mfm_config["master_fm"]["mfm_port"],
        ws_scheme=mfm_config["master_fm"]["ws_scheme"],
        ws_suffix=mfm_config["master_fm"]["ws_suffix"],
        cert_file=mfm_config["master_fm"]["mfm_cert_file"],
        x_api_key=mfm_config["master_fm"]["comms"]["api_key"],
        update_freq=mfm_config["master_fm"]["comms"]["update_freq"],
        ws_update_freq=mfm_config["master_fm"]["comms"]["ws_update_freq"],
    )

    return mfm_context
