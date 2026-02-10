import logging
from logging import WARNING
import os
import redis
from rq import Queue
import json
from rq import Connection, Worker

# ati code imports
import utils.util as utils_util


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

    all_sherpas = []
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
                    f"{sherpa}_misc_update_handler": Queue(
                        f"{sherpa}_misc_update_handler", connection=redis_conn
                    )
                }
            )

    queues_dict.update(
        {"resource_handler": Queue("resource_handler", connection=redis_conn)}
    )
    queues_dict.update({"generic_handler": Queue("generic_handler", connection=redis_conn)})
    queues_dict.update({"misc_handler": Queue("misc_handler", connection=redis_conn)})
    queues_dict.update({"analytics_handler": Queue("analytics_handler", connection=redis_conn)})

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


def signal_job_completion(job_id, redis_conn):
    job_completion_key = f"job_{job_id}_completion"
    redis_conn.rpush(job_completion_key, "completed")

def find_type_in_args(args):
    for arg in args:
        if hasattr(arg, 'type'):
            return arg.type
    return None


def report_failure(job, connection, fail_type, value, traceback):
    # set error value
    job.meta["fail_type"] = fail_type
    job.meta["error_value"] = value
    job.save()

    type_value = find_type_in_args(job.args)
    if type_value is None:
        type_value = job.args

    logging.getLogger().error(
        f"RQ job failed: error: {fail_type}, value {value}, func: {job.func_name}, timeout: {job.timeout}, ttl: {job.ttl}, args: {job.args}, kwargs: {job.kwargs} message_type: {type_value}",
        exc_info=(fail_type, value, traceback), 
    )
    
    error_dict = {
        "error_type": str(fail_type),
        "error_msg": value,
        "Job arguments": job.type_value,
        "module": job.func_name,
        "code": "rq",
    }
    utils_util.write_fm_error_to_json_file("rq_failure", error_dict)
    # signal_job_completion(job.id, connection)


def report_success(job, connection, result, *args, **kwargs):
    pass
    # signal_job_completion(job.id, connection)


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
