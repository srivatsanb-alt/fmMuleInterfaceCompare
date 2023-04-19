import redis
import time
import toml
import asyncio
import os
from rq import Queue, Worker, Connection
from rq.job import Job
from multiprocessing import Process
from fastapi import HTTPException
import logging
import logging.config
import json

# setup logging
log_conf_path = os.path.join(os.getenv("FM_CONFIG_DIR"), "plugin_logging.conf")
logging.config.fileConfig(log_conf_path)
logger = logging.getLogger("plugin_rq")


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
    logger = logging.getLogger("plugin_rq")
    logger.error(
        f"RQ job failed: error: {fail_type}, value: {value} func: {job.func_name}, args: {job.args}, kwargs: {job.kwargs}",
        exc_info=(fail_type, value, traceback),
    )


def report_success(job, connection, result, *args, **kwargs):
    logger = logging.getLogger("plugin_rq")
    logger.info(f"job done successfully {job}")
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


async def get_job_result(job_id):
    redis_conn = redis.from_url(os.getenv("FM_REDIS_URI"))
    job = Job.fetch(job_id, connection=redis_conn)
    while True:
        status = job.get_status(refresh=True)
        if status == "finished":
            response = job.result
            break
        if status == "failed":
            job.cancel()
            raise HTTPException(status_code=500, detail="Unable to process the request")
        await asyncio.sleep(0.01)

    return response


if __name__ == "__main__":
    time.sleep(30)

    redis_conn = get_redis_conn()
    all_plugins = get_all_plugins()

    if "ies" in all_plugins:
        from ies.ies_utils import TripsIES
        from plugin_db import init_db

        ies_logger = logging.getLogger("plugin_ies")
        init_db(str("plugin_ies"), [TripsIES])

        # # start a worker for ies plugin
        Process(target=start_worker, args=("plugin_ies",)).start()
        ies_logger.info("started a worker for plugin_ies")

        from ies.ies_job_updates import check_status_and_combine_trips, send_job_updates

        Process(target=send_job_updates, args=[]).start()
        ies_logger.info("Sending continuous job updates")

        def ies_combine_trips_handler():
            return asyncio.get_event_loop().run_until_complete(
                check_status_and_combine_trips()
            )

        Process(target=ies_combine_trips_handler, args=[]).start()
        ies_logger.info("Starting ies combine trips handler")

    if "ies_v2" in all_plugins:
        import ies_v2.ies_v2_models as im
        from plugin_db import init_db

        ies_v2_logger = logging.getLogger("plugin_ies_v2")
        init_db(str("plugin_ies_v2"), [im.CombinedTripsv2, im.JobIES])

        Process(target=start_worker, args=("plugin_ies_v2",)).start()
        ies_v2_logger.info("started a worker for plugin_ies_v2")

    if "conveyor" in all_plugins:
        import conveyor.conveyor_models as cm

        from plugin_db import init_db

        conveyor_logger = logging.getLogger("plugin_conveyor")
        init_db(str("plugin_conveyor"), [cm.ConvInfo, cm.ConvTrips])

        # IMPORT AFTER INIT DB #
        from conveyor.conveyor_utils import get_all_conveyors

        all_conveyors = get_all_conveyors()
        conveyor_logger.info(f"Populated conveyor_info table with info of {all_conveyors}")

        # start a worker for conveyor plugin
        for conveyor_name in all_conveyors:
            Process(target=start_worker, args=(f"plugin_conveyor_{conveyor_name}",)).start()
            conveyor_logger.info(f"started a worker for plugin_conveyor_{conveyor_name}")

    if "summon_button" in all_plugins:
        from summon_button.summon_utils import (
            SummonInfo,
            SummonActions,
        )
        from plugin_db import init_db

        summon_logger = logging.getLogger("plugin_summon_button")
        init_db(str("plugin_summon_button"), [SummonInfo, SummonActions])
        create_dummy_queue = Queue("plugin_summon_button", connection=redis_conn)
        Process(target=start_worker, args=("plugin_summon_button",)).start()
        summon_logger.info("started a worker for plugin_summon_button")
        from summon_button.summon_utils import send_job_updates_summon

        Process(target=send_job_updates_summon, args=[]).start()
        summon_logger.info("Sending periodic job updates")

    redis_conn.set("plugins_workers_db_init", json.dumps(True))
