import time
import logging

# ati code imports
import models.request_models as rqm
from app.routers.dependencies import process_req
from utils.rq_utils import Queues


def misc_processes():
    logging.getLogger().info("started periodic misc_processes script")
    while True:
        try:
            misc_process = rqm.MiscProcess(ttl=2)
            q = Queues.queues_dict.get("misc_handler")
            process_req(q, misc_process, "self")
        except Exception as e:
            logging.getLogger().info(f"exception in periodic misc_processes script {e}")

        time.sleep(15 * 60)
