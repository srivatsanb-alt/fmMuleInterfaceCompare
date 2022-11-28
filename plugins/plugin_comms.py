import aioredis
import os
import ast
import requests
import logging
from app.routers.dependencies import generate_jwt_token
from plugins.plugin_rq import Plugin_Queues, enqueue

logging.basicConfig(level=logging.INFO)


async def ws_reader(websocket, name, handler_obj):
    plugin_q = Plugin_Queues.queues_dict[f"plugin_{name}"]
    logging.info(f"Started websocket reader for {name}")
    while True:
        msg = await websocket.receive_json()
        logging.info(f"Got a plugin msg {msg}")
        enqueue(plugin_q, handler_obj.handle, msg)


async def ws_writer(websocket, name):
    redis_conn = aioredis.Redis.from_url(
        os.getenv("FM_REDIS_URI"), max_connections=10, decode_responses=True
    )
    psub = redis_conn.pubsub()

    # subscribe redis message/data queue - similar to bus
    await psub.subscribe(f"channel:plugin_{name}")

    logging.info(f"Started websocket writer for {name}")

    while True:
        message = await psub.get_message(ignore_subscribe_messages=True, timeout=5)
        if message:
            # logging.info(f"Got a message ws_writer {message}")
            data = ast.literal_eval(message["data"])
            await websocket.send_json(data)


def check_response(response):
    response_json = None
    if response.status_code == 200:
        response_json = response.json()
    return response.status_code, response_json


def send_req_to_FM(plugin_name, endpoint, req_type, req_json=None, query=""):

    url = get_fm_url(endpoint, query)

    if url is None:
        logging.getLogger(plugin_name).info(
            f"cannot fetch fleet_manager url for endpoint {endpoint}"
        )
        raise ValueError(f"cannot fetch fleet_manager url for endpoint {endpoint}")

    token = generate_jwt_token(plugin_name)

    logging.getLogger(plugin_name).info(
        f"Request to be sent to fleet manager \n plugin_name: {plugin_name} \n url: {url}, method: {req_type} \n body: {req_json}"
    )

    req_method = getattr(requests, req_type)
    args = [url]
    kwargs = {"headers": {"X-User-Token": token}}

    if req_json:
        kwargs.update({"json": req_json})

    response = req_method(*args, **kwargs)
    response_status_code, response_json = check_response(response)

    logging.getLogger(plugin_name).info(
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
            "http://", fm_ip, "api/v1/trips/ongoing/", str(query)
        ),
        "delete_booked_trip": os.path.join(
            "http://", fm_ip, "api/v1/trips/booking/", str(query)
        ),
    }
    return fm_endpoints.get(endpoint, None)
