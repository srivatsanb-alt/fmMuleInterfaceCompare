import logging
from logging import WARNING
import os
import redis
from rq import Queue
import json
from rq import Connection, Worker


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


# utils for redis rq
class Queues:
    redis_conn = redis.from_url(
        os.getenv("FM_REDIS_URI"), encoding="utf-8", decode_responses=True
    )

    queues_dict = {}
    all_sherpas = redis_conn.get("all_sherpas")
    if all_sherpas:
        all_sherpas = json.loads(all_sherpas)

    for sherpa in all_sherpas:
        queues_dict.update(
            {
                f"{sherpa}_update_handler": Queue(
                    f"{sherpa}_update_handler", connection=redis_conn
                )
            }
        )

    for sherpa in all_sherpas:
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
    queues_dict.update({"misc_handler": Queue("misc_handler", connection=redis_conn)})

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
    # set error value
    job.meta["fail_type"] = fail_type
    job.meta["error_value"] = value
    job.save()

    logging.getLogger().error(
        f"RQ job failed: error: {fail_type}, value {value}, func: {job.func_name}, timeout: {job.timeout}, ttl: {job.ttl}, args: {job.args}, kwargs: {job.kwargs}",
        exc_info=(fail_type, value, traceback),
    )


def report_success(job, connection, result, *args, **kwargs):
    pass


def enqueue(queue: Queue, func, *args, **kwargs):
    kwargs.setdefault("result_ttl", 100)
    kwargs.setdefault("failure_ttl", 0)
    kwargs.setdefault("on_failure", report_failure)
    kwargs.setdefault("on_success", report_success)
    return queue.enqueue(func, *args, **kwargs)


def enqueue_at(queue: Queue, dt, func, *args, **kwargs):
    kwargs.setdefault("result_ttl", 100)
    kwargs.setdefault("failure_ttl", 0)
    kwargs.setdefault("on_failure", report_failure)
    kwargs.setdefault("on_success", report_success)
    return queue.enqueue_at(dt, func, *args, **kwargs)
