import logging
import os
from logging import WARNING
from multiprocessing import Process

import redis
from rq import Connection, Worker

from core.config import get_fleet_mode, read_config
from core.logs import init_logging
from utils.rq import Queues


def init_fleet_manager(config):
    init_logging()
    if get_fleet_mode(config) == "flipkart":
        # TODO: load globals
        # TODO: load_ez_data
        pass


def start(queue):
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
    config = read_config()
    init_fleet_manager(config)

    Queues.add_all_queues(config)

    for q in Queues.get_queues():
        process = Process(target=start, args=(q,))
        process.start()

    logging.info("Ati Fleet Manager started")
