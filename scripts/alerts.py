import ast
import logging
import logging.config
import logging
import logging.config
import os
import aioredis
from slack_sdk.webhook import WebhookClient
import asyncio

# ati code imports
import utils.log_utils as lu
import models.misc_models as mm
from models.mongo_client import FMMongo

# setup logging
logging.config.dictConfig(lu.get_log_config_dict())
logger = logging.getLogger("misc")


async def forward_alerts(alert_config):

    slack_webhook_url = alert_config["slack_webhook_url"]
    try:
        webhook = WebhookClient(slack_webhook_url)
    except Exception as e:
        logger.info(f"unable to create WebhookClient, exception: {e}")
        return

    redis = aioredis.Redis.from_url(
        os.getenv("FM_REDIS_URI"), max_connections=10, decode_responses=True
    )
    psub = redis.pubsub()
    await psub.subscribe("channel:notifications")
    sent_notification_ids = []

    while True:
        try:
            message = await psub.get_message(ignore_subscribe_messages=True, timeout=5)
            if message:
                data = ast.literal_eval(message["data"])
                for id, details in data.items():
                    alert_sent = False
                    # to handles key-val pair like {"type": "notifications"} in the notification msg
                    if not isinstance(details, dict):
                        continue
                    elif id in sent_notification_ids:
                        continue
                    elif details.get("log_level", None) == mm.NotificationLevels.alert:
                        sent_notification_ids.append(id)
                        alert_msg = details.get("log")
                        if alert_msg:
                            entity_names = details.get("entity_names")
                            alert_msg += f"\n entity_names: {entity_names}"
                            response = webhook.send(text=alert_msg)
                        if response.status_code == 200:
                            alert_sent = True

                        if alert_sent:
                            logger.info(f"Sent alert msg: {alert_msg}")
                        else:
                            logger.warning(f"Unable to send alert msg: {alert_msg}")

        except Exception as e:
            logger.error(f"Exception in alerts script, exception: {e}")


def send_slack_alerts():

    with FMMongo() as fm_mongo:
        alert_config = fm_mongo.get_document_from_fm_config("alerts")

    notifications = alert_config["notifications"]
    logger.info(f"Started send_slack_alerts script")

    if notifications is not True:
        logger.info("slack alerts notification is set to false")
        return

    asyncio.get_event_loop().run_until_complete(forward_alerts(alert_config))
