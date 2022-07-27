import logging
import os
import redis
from rq import Queue
from core.config import get_fleet_mode
from core.db import session_maker
from models.fleet_models import Fleet, Sherpa


class Queues:

    redis_conn = redis.from_url(
        os.getenv("FM_REDIS_URI"), encoding="utf-8", decode_responses=True
    )
    from_frontend_queue = Queue("from_frontend", connection=redis_conn)
    to_sherpa_queue = Queue("to_sherpa", connection=redis_conn)
    to_frontend_queue = Queue("to_frontend", connection=redis_conn)
    handler_queue = Queue("to_handlers", connection=redis_conn)

    @classmethod
    def add_queue(cls, name):
        setattr(cls, name, Queue(name, connection=cls.redis_conn))


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


def get_queues(config):
    with session_maker() as db:
        db_fleets = db.query(Fleet).all()

    fleet_mode = get_fleet_mode(config)

    with session_maker() as db:
        for fleet in db_fleets:
            db_sherpas = db.query(Sherpa).filter(Sherpa.fleet_id == fleet.id).all()
        for sherpa in db_sherpas:
            Queues.add_queue("from_sherpa_" + sherpa.name)
        if fleet_mode == "flipkart":
            # TODO: add conveyor queues.
            pass
