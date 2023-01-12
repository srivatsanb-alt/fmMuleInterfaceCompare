from rq import Queue, Worker, Connection
from rq.job import Job
import redis
import time
import toml
import os
from multiprocessing import Process
from fastapi import HTTPException
import logging
import json

logging.basicConfig(level=logging.INFO)


def get_seperate_logger(name):
    logger = logging.getLogger(name)
    FORMATTER = logging.Formatter("%(asctime)s %(levelname)s [%(funcName)s] %(message)s")
    logger.propagate = False
    log_file = os.path.join(os.getenv("FM_LOG_DIR"), f"{name}.log")
    logger.setLevel(logging.INFO)
    f_handler = logging.FileHandler(log_file)
    f_handler.setFormatter(FORMATTER)
    logger.addHandler(f_handler)
    return logger


def get_redis_conn():
    redis_conn = redis.from_url(
        os.getenv("FM_REDIS_URI"), encoding="utf-8", decode_responses=True
    )

    return redis_conn


def get_plugin_config():
    plugin_config = toml.load(
        os.path.join(os.getenv("FM_CONFIG_DIR"), "plugin_config.toml")
    )
    return plugin_config


def get_all_plugins():
    return get_plugin_config()["all_plugins"]


class Plugin_Queues:
    queues_dict = {}
    all_plugins = get_all_plugins()

    for plugin_name in all_plugins:
        queues_dict.update(
            {
                f"plugin_{plugin_name}": Queue(
                    f"plugin_{plugin_name}", connection=get_redis_conn()
                )
            }
        )

    @classmethod
    def get_queue(cls, qname):
        return getattr(cls, qname)


def start_worker(queue_name):
    with Connection():
        Worker.log_result_lifespan = False
        worker = Worker(
            queue_name,
            disable_default_exception_handler=True,
            log_job_description=False,
            connection=redis.from_url(os.getenv("FM_REDIS_URI")),
        )
        worker.work(logging_level=logging.WARNING, with_scheduler=True)


def report_failure(job, connection, fail_type, value, traceback):
    logging.info(
        f"RQ job failed: error: {fail_type}, func: {job.func_name}, args: {job.args}, kwargs: {job.kwargs}"
    )


def report_success(job, connection, result, *args, **kwargs):
    pass


def enqueue(queue: Queue, func, *args, **kwargs):
    kwargs.setdefault("result_ttl", 100)
    kwargs.setdefault("failure_ttl", 0)
    kwargs.setdefault("on_failure", report_failure)
    kwargs.setdefault("on_success", report_success)
    return queue.enqueue(
        func,
        *args,
        **kwargs,
    )


def get_job_result(job_id):
    job = Job.fetch(job_id, connection=redis_conn)
    while True:
        status = job.get_status(refresh=True)
        if status == "finished":
            response = job.result
            break
        if status == "failed":
            job.cancel()
            raise HTTPException(status_code=500, detail="Unable to process the request")
        time.sleep(0.01)

    return response


if __name__ == "__main__":
    time.sleep(30)

    redis_conn = get_redis_conn()
    all_plugins = get_all_plugins()

    if "ies" in all_plugins:
        from ies.ies_utils import TripsIES
        from plugin_db import init_db

        ies_logger = get_seperate_logger("plugin_ies")
        init_db(str("plugin_ies"), [TripsIES])

        # # start a worker for ies plugin
        Process(target=start_worker, args=("plugin_ies",)).start()
        ies_logger.info("started a worker for plugin_ies")

        from ies.ies_job_updates import send_job_updates

        Process(target=send_job_updates, args=[]).start()
        ies_logger.info("Sending periodic job updates")

    if "conveyor" in all_plugins:
        from conveyor.conveyor_utils import ConvInfo, ConvTrips, populate_conv_info
        from plugin_db import init_db

        conveyor_logger = get_seperate_logger("plugin_conveyor")
        init_db(str("plugin_conveyor"), [ConvInfo, ConvTrips])

        all_conveyors = populate_conv_info()

        conveyor_logger.info("Populated conveyor_info table")

        # start a worker for conveyor plugin
        for conveyor_name in all_conveyors:
            Process(target=start_worker, args=(f"plugin_conveyor_{conveyor_name}",)).start()
            conveyor_logger.info(f"started a worker for plugin_conveyor_{conveyor_name}")

    redis_conn.set("plugins_workers_db_init", json.dumps(True))
