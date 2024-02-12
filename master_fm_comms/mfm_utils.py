import logging
import os
import requests
from dataclasses import dataclass
from requests.auth import HTTPBasicAuth

# ati code imports
from models.mongo_client import FMMongo


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
    send_updates: bool


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
        "upload_map_file": os.path.join(
            mfm_url, "api/v1/master_fm/fm_client/upload_map_file", str(query)
        ),
        "reset_map_dir": os.path.join(
            mfm_url, "api/v1/master_fm/fm_client/reset_map_dir", str(query)
        ),
        "update_trip_info": os.path.join(
            mfm_url, "api/v1/master_fm/fm_client/update_trip_info"
        ),
        "update_trip_analytics": os.path.join(
            mfm_url, "api/v1/master_fm/fm_client/update_trip_analytics"
        ),
        "update_fm_version_info": os.path.join(
            mfm_url, "api/v1/master_fm/fm_client/update_fm_version_info"
        ),
        "update_fm_incidents": os.path.join(
            mfm_url, "api/v1/master_fm/fm_client/add_fm_incidents"
        ),
        "update_sherpa_oee": os.path.join(
            mfm_url, "api/v1/master_fm/fm_client/update_sherpa_oee"
        ),
        "upload_file": os.path.join(mfm_url, "api/v1/master_fm/fm_client/upload_file"),
        "get_available_updates": os.path.join(
            mfm_url, "api/v1/master_fm/fm_client/get_available_updates", str(query)
        ),
        "download_file": os.path.join(mfm_url, "api/static/downloads", str(query)),
        "get_basic_auth": os.path.join(mfm_url, "api/v1/master_fm/user/get_basic_auth"),
    }
    return fm_endpoints.get(endpoint, None)


def check_response(response):
    response_json = None
    if response.status_code == 200:
        try:
            response_json = response.json()
        except:
            # could be downloadable file
            response_json = response.content
    return response.status_code, response_json


def send_http_req_to_mfm(
    mfm_context,
    endpoint,
    req_type,
    req_json=None,
    files=None,
    params=None,
    query="",
    auth=None,
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

    if params:
        kwargs.update({"params": params})

    if auth:
        kwargs.update({"auth": auth})

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
    with FMMongo() as fm_mongo:
        mfm_config = fm_mongo.get_document_from_fm_config("master_fm")

    mfm_context = MFMContext(
        http_scheme=mfm_config["http_scheme"],
        server_ip=mfm_config["mfm_ip"],
        server_port=mfm_config["mfm_port"],
        ws_scheme=mfm_config["ws_scheme"],
        ws_suffix=mfm_config["ws_suffix"],
        cert_file=mfm_config["mfm_cert_file"],
        x_api_key=mfm_config["api_key"],
        update_freq=mfm_config["update_freq"],
        ws_update_freq=mfm_config["ws_update_freq"],
        send_updates=mfm_config["send_updates"],
    )

    if mfm_context.send_updates is False:
        logging.getLogger("mfm_updates").info("Send updates set/default to False")

    return mfm_context


def prune_fleet_status(fleet_status_msg: dict):
    pruned_msg = {}
    pruned_msg.update({"type": "fleet_status"})
    pruned_msg.update({"fleet_name": fleet_status_msg["fleet_name"]})

    new_sherpa_status = {}
    for sherpa_name, sherpa_status in fleet_status_msg["sherpa_status"].items():
        pruned_sherpa_status = {}
        pruned_sherpa_status.update({"sherpa_name": sherpa_name})
        pruned_sherpa_status.update({"mode": sherpa_status["mode"]})
        pruned_sherpa_status.update({"initialized": sherpa_status["initialized"]})
        pruned_sherpa_status.update({"inducted": sherpa_status["inducted"]})
        pruned_sherpa_status.update({"disabled": sherpa_status["disabled"]})
        pruned_sherpa_status.update({"disabled_reason": sherpa_status["disabled_reason"]})
        pruned_sherpa_status.update({"idle": sherpa_status["idle"]})
        pruned_sherpa_status.update({"error": sherpa_status["error"]})
        pruned_sherpa_status.update({"pose": sherpa_status["pose"]})
        pruned_sherpa_status.update({"trip_id": sherpa_status["trip_id"]})
        pruned_sherpa_status.update({"battery_status": sherpa_status["battery_status"]})
        pruned_sherpa_status.update({"ip_address": sherpa_status["ip_address"]})
        #pruned_sherpa_status.update({"other_info": sherpa_status["other_info"]})

        # update new_sherpa_status
        new_sherpa_status.update({sherpa_name: pruned_sherpa_status})

    pruned_msg.update({"sherpa_status": new_sherpa_status})

    return pruned_msg


def get_mfm_static_file_auth(mfm_context):
    status_code, auth_json = send_http_req_to_mfm(
        mfm_context=mfm_context,
        endpoint="get_basic_auth",
        req_type="get",
    )

    if status_code != 200:
        return None, None

    static_files_auth_username = auth_json["static_files_auth"]["username"]
    static_files_auth_password = auth_json["static_files_auth"]["password"]
    auth = HTTPBasicAuth(static_files_auth_username, static_files_auth_password)

    return auth, auth_json


def get_available_updates_fm(mfm_context):
    status_code, available_updates_json = send_http_req_to_mfm(
        mfm_context=mfm_context,
        endpoint="get_available_updates",
        req_type="get",
        query="fm",
    )
    return status_code, available_updates_json


def get_release_details(mfm_context, fm_version, auth):
    release_notes = None
    release_dt = None
    status_code, release_dt = send_http_req_to_mfm(
        mfm_context=mfm_context,
        endpoint="download_file",
        req_type="get",
        query=f"fm/{fm_version}/release.dt",
        auth=auth,
    )
    if status_code == 200:
        if release_dt is not None:
            release_dt = release_dt.decode()

    status_code, release_notes = send_http_req_to_mfm(
        mfm_context=mfm_context,
        endpoint="download_file",
        req_type="get",
        query=f"fm/{fm_version}/release.notes",
        auth=auth,
    )

    if status_code == 200:
        if release_notes is not None:
            release_notes = release_notes.decode()

    return release_notes, release_dt
