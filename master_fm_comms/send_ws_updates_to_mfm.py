import websockets
import ast
import logging
import ssl
import asyncio
import aioredis
import os
import datetime
import json

# ati code imports
import master_fm_comms.mfm_utils as mu


async def send_ongoing_trip_status(ws, mfm_context: mu.MFMContext):
    redis = aioredis.Redis.from_url(
        os.getenv("FM_REDIS_URI"), max_connections=10, decode_responses=True
    )
    psub = redis.pubsub()
    await psub.subscribe("channel:status_updates")

    all_fleet_names = await redis.get("all_fleet_names")
    all_fleet_names = json.loads(all_fleet_names)

    last_update_dt = {}
    for fleet_name in all_fleet_names:
        last_update_dt.update({fleet_name: datetime.datetime.now()})

    while True:
        message = await psub.get_message(ignore_subscribe_messages=True, timeout=5)
        if message:
            data = ast.literal_eval(message["data"])

            if data.get("type") != "ongoing_trips_status":
                continue

            elif not data.get("fleet_name"):
                continue

            fleet_name = data.get("fleet_name")
            time_delta = datetime.datetime.now() - last_update_dt.get(fleet_name)

            if time_delta.seconds > mfm_context.ws_update_freq:
                await ws.send(json.dumps(data))
                last_update_dt.update({fleet_name: datetime.datetime.now()})
                logging.getLogger("mfm_updates").info(
                    f"sent an ongoing_trip status msg for {fleet_name} to master fm"
                )


async def send_fleet_status(ws, mfm_context: mu.MFMContext):
    redis = aioredis.Redis.from_url(
        os.getenv("FM_REDIS_URI"), max_connections=10, decode_responses=True
    )
    psub = redis.pubsub()
    await psub.subscribe("channel:status_updates")

    all_fleet_names = await redis.get("all_fleet_names")
    all_fleet_names = json.loads(all_fleet_names)

    last_update_dt = {}
    for fleet_name in all_fleet_names:
        last_update_dt.update({fleet_name: datetime.datetime.now()})

    while True:
        message = await psub.get_message(ignore_subscribe_messages=True, timeout=5)
        if message:
            data = ast.literal_eval(message["data"])

            if data.get("type") != "fleet_status":
                continue

            elif not data.get("fleet_name"):
                continue

            fleet_name = data.get("fleet_name")
            time_delta = datetime.datetime.now() - last_update_dt.get(fleet_name)

            if time_delta.seconds > mfm_context.ws_update_freq:
                pruned_fleet_status = mu.prune_fleet_status(data)

                await ws.send(json.dumps(pruned_fleet_status))

                last_update_dt.update({fleet_name: datetime.datetime.now()})
                logging.getLogger("mfm_updates").info(
                    f"sent a fleet_status msg for {fleet_name} to master fm"
                )


async def async_send_ws_msgs_to_mfm():
    logging.getLogger("mfm_updates").info("started async_send_ws_msgs_to_mfm script")
    mfm_context: mu.MFMContext = mu.get_mfm_context()

    while True:
        ssl_context = ssl.SSLContext()
        ssl_context.verify_mode = ssl.CERT_REQUIRED
        ws_url = mu.get_mfm_ws_url(mfm_context)

        if "wss" in ws_url:
            ssl_context.load_verify_locations(mfm_context.cert_file)
        else:
            ssl_context = None

        ssl_context_set = True if ssl_context else False
        try:
            logging.getLogger("mfm_updates").info(
                f"Will attempt to connect to {ws_url}, is ssl_context set {ssl_context_set}"
            )
            async with websockets.connect(
                ws_url,
                ssl=ssl_context,
                extra_headers=(("X-API-Key", mfm_context.x_api_key),),
            ) as ws:
                logging.getLogger("mfm_updates").info(f"connected to {ws_url}")
                await asyncio.gather(
                    send_ongoing_trip_status(ws, mfm_context),
                    send_fleet_status(ws, mfm_context),
                )

        except Exception as e:
            sl = 10
            logging.getLogger("mfm_updates").info(
                f"websocket disconnected, {e}. will try to reconnect in {sl} seconds..."
            )
            await asyncio.sleep(sl)

    logging.getLogger("mfm_updates").info("closed websocket connection with fleet manager")


def send_ws_msgs_to_mfm():
    asyncio.get_event_loop().run_until_complete(async_send_ws_msgs_to_mfm())
