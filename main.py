from logging import WARNING
import logging
from multiprocessing import Process
import os

import redis
from core.config import get_fleet_mode, read_config
from core.logs import init_logging
from rq import Connection, Worker

from utils.rq import get_queues


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
            connection=redis.from_url(os.getenv("HIVEMIND_REDIS_URI")),
        )
        worker.work(logging_level=WARNING, with_scheduler=True)


if __name__ == "__main__":
    config = read_config()
    init_fleet_manager(config)

    queues = get_queues(config)

    for q in queues:
        process = Process(target=start, args=(q,))
        process.start()

    logging.info("Ati Fleet Manager started")
