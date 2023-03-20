import time
import logging

# ati code imports
from models.request_models import FMHealthCheck
from app.routers.dependencies import process_req
from utils.rq_utils import Queues


def periodic_health_check():
    logging.getLogger().info(f"started periodic_health_check script")
    while True:
        try:
            fm_health_check = FMHealthCheck()
            q = Queues.queues_dict.get("misc_handler")
            process_req(q, fm_health_check, "self", ttl=2)
        except Exception as e:
            logging.getLogger().info(f"exception in periodic fm fm_health_check script {e}")

        time.sleep(10)
