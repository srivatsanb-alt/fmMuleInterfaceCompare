import logging
import os
from logging import WARNING
from multiprocessing import Process

import json
import redis
from rq import Connection, Worker

from core.config import Config
from core.logs import init_logging
from utils.rq_utils import Queues

from scripts.periodic_updates import send_periodic_updates
from scripts.periodic_backup import backup_data
from scripts.periodic_assigner import assign_next_task
from scripts.alerts import send_slack_alerts


def init_fleet_manager(config):
    init_logging()
    if Config.get_fleet_mode() == "flipkart":
        # TODO: load globals
        pass


def start_worker(queue):
    with Connection():
        Worker.log_result_lifespan = False
        worker = Worker(
            queue,
            disable_default_exception_handler=True,
            log_job_description=False,
            connection=redis.from_url(os.getenv("FM_REDIS_URI")),
        )
        logging.info(f"Started worker for queue {queue}")
        worker.work(logging_level=WARNING, with_scheduler=True)


if __name__ == "__main__":
    redis_conn = redis.from_url(os.getenv("FM_REDIS_URI"))

    config = Config.read_config()
    init_fleet_manager(config)

    logging.info(f"all queues {Queues.get_queues()}")

    for q in Queues.get_queues():
        process = Process(target=start_worker, args=(q,))
        process.start()

    # send periodic status update
    Process(target=send_periodic_updates).start()

    # start periodic assigner scripts
    Process(target=assign_next_task).start()

    # start backup data
    Process(target=backup_data).start()

    # start send slack alerts script
    Process(target=send_slack_alerts).start()

    redis_conn.set("is_fleet_manager_up", json.dumps(True))
    logging.info("Ati Fleet Manager started")
