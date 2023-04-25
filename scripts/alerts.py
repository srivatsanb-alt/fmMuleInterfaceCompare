import time
import os
import logging
import logging.config
from slack_sdk.webhook import WebhookClient


from core.config import Config
from models.db_session import DBSession
from models.fleet_models import SherpaStatus


# setup logging
log_conf_path = os.path.join(os.getenv("FM_MISC_DIR"), "logging.conf")
logging.config.fileConfig(log_conf_path)
logger = logging.getLogger("misc")


def send_slack_alerts():
    fleet_config = Config.read_config()
    alert_config = fleet_config.get("alerts", {})

    notifications = alert_config.get("notifications", False)
    time_interval = alert_config.get("time_interval", 30)
    # slack_webhook_url = "https://hooks.slack.com/services/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"
    slack_webhook_url = alert_config.get("slack_webhook_url")

    logger.info(f"Started send_slack_alerts script, slack_webhook_url: {slack_webhook_url}")

    webhook = WebhookClient(slack_webhook_url)

    if not notifications:
        logger.info("slack alerts notification is set to false")
        return

    if slack_webhook_url is None:
        logger.info("slack webhook url not present")
        return

    all_previous_error = {}
    sherpa_names = []
    while True:
        with DBSession() as dbsession:
            sherpas_with_error = (
                dbsession.session.query(SherpaStatus)
                .filter(SherpaStatus.mode == "error")
                .all()
            )

            for sherpa_with_previous_errors in list(all_previous_error):
                if sherpa_with_previous_errors not in sherpa_names:
                    logger.info(
                        f"sherpa {sherpa_with_previous_errors} is no longer in error mode, the error was {all_previous_error[sherpa_with_previous_errors]}"
                    )
                    del all_previous_error[sherpa_with_previous_errors]
            sherpa_names = []
            for sherpa in sherpas_with_error:
                sherpa_names.append(sherpa.sherpa_name)
                previous_error = all_previous_error.get(sherpa.sherpa_name)
                if previous_error == sherpa.error:
                    pass
                else:
                    body = f":warning: sherpa {sherpa.sherpa_name} in {sherpa.mode} mode: {sherpa.error}"
                    response = webhook.send(text=body)

                    if response.status_code == 200:
                        logger.info(
                            f"slack alert sent, sherpa {sherpa.sherpa_name} in {sherpa.mode} mode: {sherpa.error}"
                        )
                    else:
                        logger.info(
                            f"slack alert not sent, sherpa {sherpa.sherpa_name} in {sherpa.mode} mode: {sherpa.error}"
                        )

                    all_previous_error[sherpa.sherpa_name] = sherpa.error
        time.sleep(time_interval)
