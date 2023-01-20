import logging
import os
import redis
from rq import Queue
from core.config import Config


class Queues:

    redis_conn = redis.from_url(
        os.getenv("FM_REDIS_URI"), encoding="utf-8", decode_responses=True
    )

    queues_dict = {}
    all_sherpas = Config.get_all_sherpas()
    all_fleets = Config.get_all_fleets()

    for sherpa in all_sherpas.keys():
        queues_dict.update(
            {
                f"{sherpa}_update_handler": Queue(
                    f"{sherpa}_update_handler", connection=redis_conn
                )
            }
        )

    for sherpa in all_sherpas.keys():
        queues_dict.update(
            {
                f"{sherpa}_trip_update_handler": Queue(
                    f"{sherpa}_trip_update_handler", connection=redis_conn
                )
            }
        )

    queues_dict.update(
        {"resource_handler": Queue("resource_handler", connection=redis_conn)}
    )
    queues_dict.update({"generic_handler": Queue("generic_handler", connection=redis_conn)})
    queues_dict.update({"misc": Queue("misc_handler", connection=redis_conn)})

    queues = [q_name for q_name in queues_dict.keys()]

    @classmethod
    def add_queue(cls, name):
        cls.queues_dict.update({name: Queue(name, connection=cls.redis_conn)})
        cls.queues.append(name)

    @classmethod
    def get_queues(cls):
        return cls.queues

    @classmethod
    def get_queue(cls, qname):
        return getattr(cls, qname)


def report_failure(job, connection, fail_type, value, traceback):
    logging.getLogger().error(
        f"RQ job failed: error: {fail_type}, value {value}, func: {job.func_name}, args: {job.args}, kwargs: {job.kwargs}",
        exc_info=(fail_type, value, traceback),
    )


def report_success(job, connection, result, *args, **kwargs):
    pass


def enqueue(queue: Queue, func, *args, **kwargs):
    kwargs.setdefault("result_ttl", 100)
    kwargs.setdefault("failure_ttl", 0)
    kwargs.setdefault("job_timeout", 15)
    kwargs.setdefault("on_failure", report_failure)
    kwargs.setdefault("on_success", report_success)
    return queue.enqueue(
        func,
        *args,
        **kwargs,
    )


def enqueue_at(queue: Queue, dt, func, *args, **kwargs):
    kwargs.setdefault("result_ttl", 100)
    kwargs.setdefault("failure_ttl", 0)
    kwargs.setdefault("on_failure", report_failure)
    kwargs.setdefault("on_success", report_success)
    return queue.enqueue_at(
        dt,
        func,
        *args,
        **kwargs,
    )
