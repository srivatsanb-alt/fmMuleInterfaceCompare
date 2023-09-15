import asyncio
import logging
import logging.config
import aioredis
import os
import ast
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm.attributes import flag_modified

# ati code imports
import app.routers.dependencies as dpd
from models.db_session import DBSession
import utils.log_utils as lu
import models.misc_models as mm

# module regarding the http and websocket notifications(read, write, delete)


# get  logging
logging.config.dictConfig(lu.get_log_config_dict())
logger = logging.getLogger("uvicorn")


router = APIRouter(tags=["notifications"], responses={404: {"description": "Not found"}})


@router.get("/api/v1/notification/basic_info")
async def get_all_notification_modules(user_name=Depends(dpd.get_user_from_query)):
    response = {}

    all_notif_mods = [
        i for i in list(mm.NotificationModules.__dict__.keys()) if not i.startswith("__")
    ]
    all_notif_levels = [
        i for i in list(mm.NotificationLevels.__dict__.keys()) if not i.startswith("__")
    ]

    response.update({"notification_modules": all_notif_mods})
    response.update({"notification_levels": all_notif_levels})

    return response


@router.delete("/api/v1/notification/clear/{id}/{token}")
async def clear_notification(
    id: int, token: str, user_name=Depends(dpd.get_user_from_query)
):

    response = {}
    if not user_name:
        dpd.raise_error("Unknown requeter")

    with DBSession() as dbsession:
        notification = dbsession.get_notifications_with_id(id)
        if not notification:
            dpd.raise_error(f"No notification found with id: {id}")

        if notification.cleared_by is None:
            notification.cleared_by = []

        notification.cleared_by.append(token)
        flag_modified(notification, "cleared_by")

    return response


@router.get("/api/v1/notifications/clear_all/{token}")
async def clear_notifications(token: str, user_name=Depends(dpd.get_user_from_query)):
    response = {}
    if not user_name:
        dpd.raise_error("Unknown requeter")

    with DBSession() as dbsession:
        all_notifications = dbsession.get_notifications()
        for notification in all_notifications:

            if notification.cleared_by is None:
                notification.cleared_by = []

            notification.cleared_by.append(token)
            flag_modified(notification, "cleared_by")

    return response


@router.websocket("/ws/api/v1/notifications/{token}")
async def notifications(
    websocket: WebSocket,
    token: str,
    user_name=Depends(dpd.get_user_from_query),
    x_real_ip=Depends(dpd.get_real_ip_from_header),
):

    client_ip = websocket.client.host
    if x_real_ip is None:
        x_real_ip = client_ip

    if not user_name:
        logger.info(
            f"websocket connection(notifications) request from (ip: {x_real_ip}) will be turned down, Unknown user"
        )
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()

    rw = [
        asyncio.create_task(reader(websocket, token, x_real_ip)),
        asyncio.create_task(
            writer(websocket, token, x_real_ip),
        ),
    ]

    try:
        await asyncio.gather(*rw)
    except Exception:
        [t.cancel() for t in rw]
    finally:
        [t.cancel() for t in rw]


async def reader(websocket, token, x_real_ip):
    while True:
        try:
            _ = await websocket.receive_json()
            pass
        except WebSocketDisconnect as e:
            logger.info(f"websocket(notifications) with {x_real_ip} disconnected")
            raise e


async def writer(websocket, token, x_real_ip):
    redis = aioredis.Redis.from_url(
        os.getenv("FM_REDIS_URI"), max_connections=10, decode_responses=True
    )
    psub = redis.pubsub()
    await psub.subscribe("channel:notifications")

    while True:
        message = await psub.get_message(ignore_subscribe_messages=True, timeout=5)
        if message:
            try:
                notification = {}
                data = ast.literal_eval(message["data"])
                for id, details in data.items():
                    # to handles key-val pair like {"type": "notifications"} in the notification msg
                    if not isinstance(details, dict):
                        notification.update({id: details})

                    # assuming that all the dicts in the message correspond a a notification
                    elif token not in details.get("cleared_by", []):
                        notification.update({id: details})
                        num_actions = len(notification[id]["cleared_by"])
                        notification[id]["num_actions"] = num_actions
                        del notification[id]["cleared_by"]

                await websocket.send_json(notification)
            except Exception as e:
                logger.error(
                    f"Exception in notification webSocket writer for {x_real_ip}, Exception: {e}"
                )
                raise e
