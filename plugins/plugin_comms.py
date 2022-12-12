import aioredis
import os
import ast
import requests
import logging
import json
from app.routers.dependencies import generate_jwt_token
from plugins.plugin_rq import Plugin_Queues, enqueue

logging.basicConfig(level=logging.INFO)


async def ws_reader(websocket, name, handler_obj, unique_id=None):
    plugin_q = Plugin_Queues.queues_dict[f"plugin_{name}"]
    logging.info(f"Started websocket reader for {name}")
    while True:
        msg_recv = await websocket.receive_text()
        logging.info(f"Received msg: {msg_recv}")
        msg = msg_recv.replace("'", '"')
        count = 0
        while type(msg) is str:
            count += 1
            msg = json.loads(msg)
        if unique_id is not None:
            msg["unique_id"] = unique_id

        logging.info(f"Converted msg: {msg}, count: {count}")
        logging.info(f"Got a plugin msg {msg}")
        enqueue(plugin_q, handler_obj.handle, msg)


async def ws_writer(websocket, name, format="json", unique_id=None):
    redis_conn = aioredis.Redis.from_url(
        os.getenv("FM_REDIS_URI"), max_connections=10, decode_responses=True
    )
    psub = redis_conn.pubsub()

    # subscribe redis message/data queue - similar to bus
    channel_name = f"plugin_{name}"
    if unique_id is not None:
        channel_name = channel_name + f"_{unique_id}"

    await psub.subscribe(f"channel:{channel_name}")
    logging.info(f"Started websocket writer for {channel_name}")

    while True:
        message = await psub.get_message(ignore_subscribe_messages=True, timeout=5)
        if message:
            logging.info(f"Got a message in {channel_name} ws_writer  {message}")

            if format == "json":
                data = ast.literal_eval(message["data"])
                await websocket.send_json(data)
            elif format == "text":
                await websocket.send_text(message["data"])


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
        "station_info": os.path.join(
            "http://", fm_ip, "api/v1/station/", str(query), "info"
        ),
    }
    return fm_endpoints.get(endpoint, None)
