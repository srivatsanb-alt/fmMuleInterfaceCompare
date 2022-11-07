import logging
import os
from logging import WARNING
from multiprocessing import Process

import redis
from rq import Connection, Worker

from core.config import Config
from core.logs import init_logging
from utils.rq import Queues

from scripts.periodic_updates import send_periodic_updates
from optimal_dispatch.router import start_router_module


def init_fleet_manager(config):
    init_logging()
    if Config.get_fleet_mode() == "flipkart":
        # TODO: load globals
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
    config = Config.read_config()
    init_fleet_manager(config)

    logging.info(f"all queues {Queues.get_queues()}")

    for q in Queues.get_queues():
        process = Process(target=start, args=(q,))
        process.start()

    # send periodic status update
    Process(target=send_periodic_updates).start()

    # start router module
    Process(target=start_router_module).start()

    logging.info("Ati Fleet Manager started")
