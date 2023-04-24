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

# module regarding the http and websocket notifications(read, write, delete)


# setup logging
log_conf_path = os.path.join(os.getenv("FM_MISC_DIR"), "logging.conf")
logging.config.fileConfig(log_conf_path)
logger = logging.getLogger("uvicorn")

router = APIRouter(tags=["notifications"], responses={404: {"description": "Not found"}})


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
            dpd.raise_error("Bad detail")

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
):
    if not user_name:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()

    rw = [
        asyncio.create_task(reader(websocket, token)),
        asyncio.create_task(
            writer(websocket, token),
        ),
    ]

    try:
        await asyncio.gather(*rw)
    except Exception:
        [t.cancel() for t in rw]
    finally:
        [t.cancel() for t in rw]


async def reader(websocket, token):
    while True:
        try:
            _ = await websocket.receive_json()
            pass
        except WebSocketDisconnect as e:
            logger.info(f"websocket with {websocket.client.host} disconnected")
            raise e


async def writer(websocket, token):
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
                    if not isinstance(details, dict):
                        notification.update({id: details})
                    elif token not in details.get("cleared_by", []):
                        notification.update({id: details})
                        num_actions = len(notification[id]["cleared_by"])
                        notification[id]["num_actions"] = num_actions
                        del notification[id]["cleared_by"]
                await websocket.send_json(notification)
            except Exception as e:
                logger.info(f"Exception in notification webSocket writer {e}")
