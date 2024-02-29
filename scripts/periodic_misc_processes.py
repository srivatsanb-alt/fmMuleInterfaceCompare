import time
import logging

# ati code imports
import models.request_models as rqm
from app.routers.dependencies import process_req
from utils.rq_utils import Queues
from utils.util import report_error


@report_error
def misc_processes():
    logging.getLogger().info("started periodic misc_processes script")
    while True:
        misc_process = rqm.MiscProcess(ttl=2)
        q = Queues.queues_dict.get("misc_handler")
        process_req(q, misc_process, "self")
        time.sleep(15 * 60)
