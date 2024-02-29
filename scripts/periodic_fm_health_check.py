import time
import logging

# ati code imports
from models.request_models import FMHealthCheck
from app.routers.dependencies import process_req
from utils.rq_utils import Queues
from utils.util import report_error


@report_error
def periodic_health_check():
    logging.getLogger().info("started periodic_health_check script")
    while True:
        fm_health_check = FMHealthCheck(ttl=2)
        q = Queues.queues_dict.get("misc_handler")
        process_req(q, fm_health_check, "self")
        time.sleep(10)
