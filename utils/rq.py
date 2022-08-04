import logging
import os

import redis
from core.config import Config
from core.db import session_maker
from models.fleet_models import Fleet, Sherpa

from rq import Queue


class Queues:

    redis_conn = redis.from_url(
        os.getenv("FM_REDIS_URI"), encoding="utf-8", decode_responses=True
    )
    from_frontend_queue = Queue("from_frontend", connection=redis_conn)
    to_frontend_queue = Queue("to_frontend", connection=redis_conn)
    to_sherpa_queue = Queue("to_sherpa", connection=redis_conn)
    handler_queue = Queue("to_handlers", connection=redis_conn)
    queues = [
        "from_frontend",
        "to_frontend",
        "to_sherpa",
        "to_handlers",
    ]

    @classmethod
    def add_all_queues(cls, config):
        with session_maker() as db:
            db_fleets = db.query(Fleet).all()

        fleet_mode = Config.get_fleet_mode()

        with session_maker() as db:
            for fleet in db_fleets:
                db_sherpas = db.query(Sherpa).filter(Sherpa.fleet_id == fleet.id).all()
                for sherpa in db_sherpas:
                    cls.add_queue("from_sherpa_" + sherpa.name)
            if fleet_mode == "flipkart":
                # TODO: add conveyor queues.
                pass

    @classmethod
    def add_queue(cls, name):
        queue = Queue(name, connection=cls.redis_conn)
        setattr(cls, name, queue)
        cls.queues.append(name)

    @classmethod
    def get_queues(cls):
        return cls.queues


def report_failure(job, connection, fail_type, value, traceback):
    logging.getLogger().error(
        f"RQ job failed: error: {fail_type}, func: {job.func_name}, args: {job.args}, kwargs: {job.kwargs}"
    )


def enqueue(queue: Queue, func, data, *args, **kwargs):
    kwargs.setdefault("result_ttl", 0)
    kwargs.setdefault("failure_ttl", 0)
    kwargs.setdefault("on_failure", report_failure)
    queue.enqueue(
        func,
        data,
        *args,
        **kwargs,
    )
