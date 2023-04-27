import aioredis
import os
import ast
import requests
import logging
import logging.config
import json
from rq import Queue
from app.routers.dependencies import generate_jwt_token
import redis
from plugins.plugin_rq import enqueue


async def ws_reader(websocket, name, handler_obj, unique_id=None, api_key=None):
    log_conf_path = os.path.join(os.getenv("FM_MISC_DIR"), "plugin_logging.conf")
    logging.config.fileConfig(log_conf_path)
    logger = logging.getLogger(f"plugin_{name}")

    if not unique_id:
        plugin_q = Queue(
            f"plugin_{name}", connection=redis.from_url(os.getenv("FM_REDIS_URI"))
        )
    else:
        plugin_q = Queue(
            f"plugin_{name}_{unique_id}",
            connection=redis.from_url(os.getenv("FM_REDIS_URI")),
        )

    logger.info(f"Started websocket reader for {name}")
    while True:
        msg_recv = await websocket.receive_text()
        logger.info(f"Received msg: {msg_recv}")
        msg = msg_recv.replace("'", '"')
        count = 0
        while type(msg) is str:
            count += 1
            msg = json.loads(msg)
        if unique_id is not None:
            msg["unique_id"] = unique_id

        if api_key:
            msg["api_key"] = api_key

        logger.info(f"Converted msg: {msg}, count: {count}")
        enqueue(plugin_q, handler_obj.handle, msg)


async def ws_writer(websocket, name, format="json", unique_id=None):

    log_conf_path = os.path.join(os.getenv("FM_MISC_DIR"), "plugin_logging.conf")
    logging.config.fileConfig(log_conf_path)
    logger = logging.getLogger(f"plugin_{name}")

    redis_conn = aioredis.Redis.from_url(
        os.getenv("FM_REDIS_URI"), max_connections=10, decode_responses=True
    )
    psub = redis_conn.pubsub()

    # subscribe redis message/data queue - similar to bus
    channel_name = f"plugin_{name}"
    if unique_id is not None:
        channel_name = channel_name + f"_{unique_id}"

    await psub.subscribe(f"channel:{channel_name}")
    logger.info(f"Started websocket writer for {channel_name}")

    while True:
        message = await psub.get_message(ignore_subscribe_messages=True, timeout=5)
        if message:
            logger.info(f"Got a message in {channel_name} ws_writer  {message}")

            if format == "json":
                data = ast.literal_eval(message["data"])

                # close WebSocket message
                if data.get("close_ws", False):
                    await websocket.close()

                await websocket.send_json(data)

            elif format == "text":
                if message["data"] == "close_ws":
                    logger.info(f"Got {channel_name} close message")
                    await websocket.close()

                await websocket.send_text(message["data"])


def check_response(response):
    response_json = None
    if response.status_code == 200:
        response_json = response.json()
    return response.status_code, response_json


def send_req_to_FM(plugin_name, endpoint, req_type, req_json=None, query=""):
    url = get_fm_url(endpoint, query)

    logger = logging.getLogger(plugin_name)

    if url is None:
        logger.info(f"cannot fetch fleet_manager url for endpoint {endpoint}")
        raise ValueError(f"cannot fetch fleet_manager url for endpoint {endpoint}")

    token = generate_jwt_token(plugin_name)

    logger.info(
        f"Request to be sent to fleet manager \n plugin_name: {plugin_name} \n url: {url}, method: {req_type} \n body: {req_json}"
    )

    req_method = getattr(requests, req_type)
    args = [url]
    kwargs = {"headers": {"X-User-Token": token}}

    if req_json:
        kwargs.update({"json": req_json})

    response = req_method(*args, **kwargs)
    response_status_code, response_json = check_response(response)

    logger.info(
        f"Response from fleet_manager \n Response status code: {response_status_code}, Response: {response_json}"
    )

    return response_status_code, response_json


def get_fm_url(endpoint, query):
    fm_ip = "127.0.0.1"
    fm_port = os.getenv("FM_PORT")
    fm_ip = fm_ip + ":" + fm_port
    fm_endpoints = {
        "trip_book": os.path.join("http://", fm_ip, "api/v1/trips/book/"),
        "trip_status": os.path.join("http://", fm_ip, "api/v1/trips/status/"),
        "delete_ongoing_trip": os.path.join(
            "http://", fm_ip, "api/v1/trips/ongoing/", str(query), "-1"
        ),
        "delete_booked_trip": os.path.join(
            "http://", fm_ip, "api/v1/trips/booking/", str(query), "-1"
        ),
        "station_info": os.path.join(
            "http://", fm_ip, "api/v1/station/", str(query), "info"
        ),
        "sherpa_summary": os.path.join(
            "http://", fm_ip, "api/v1/sherpa_summary/", str(query)
        ),
        "create_generic_alerts": os.path.join(
            "http://", fm_ip, "api/v1/create_generic_alerts/", str(query)
        ),
        "sherpa_summary": os.path.join(
            "http://", fm_ip, "api/v1/sherpa_summary/", str(query), str(0)
        ),
        "update_sherpa_metadata": os.path.join("http://", fm_ip, "api/v1/update_sherpa_metadata/"),
        "update_saved_route_info": os.path.join("http://", fm_ip, "api/v1/trips/update_saved_route_info/"),
    }
    return fm_endpoints.get(endpoint, None)


def create_fm_notification(plugin_name, alert: str):
    send_req_to_FM(plugin_name, "create_generic_alerts", "get", query=alert)
