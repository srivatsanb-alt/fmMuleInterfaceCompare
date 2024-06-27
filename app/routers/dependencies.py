import hashlib
import logging
import time
import jwt
import asyncio
from fastapi import HTTPException
from fastapi import Header
from fastapi.param_functions import Query
from rq.job import Job
import redis
import os
import json

# ati code imports
import core.handler_configuration as hc
from utils.rq_utils import enqueue, enqueue_at, Queues
from models.db_session import DBSession


# upon assignment of a task, it gets added into the job queue
def add_job_to_queued_jobs(job_id, source, redis_conn=None):
    close = False
    if redis_conn is None:
        redis_conn = redis.from_url(os.getenv("FM_REDIS_URI"))
        close = True
    queued_jobs = redis_conn.get("queued_jobs")
    if queued_jobs is None:
        queued_jobs = b"{}"

    queued_jobs = json.loads(queued_jobs)

    jobs_source = queued_jobs.get(source)

    if jobs_source is None:
        jobs_source = []
    jobs_source.append(job_id)

    queued_jobs.update({source: jobs_source})
    redis_conn.set("queued_jobs", json.dumps(queued_jobs))
    if close:
        redis_conn.close()


# removes job from the job queue
def remove_job_from_queued_jobs(job_id, source, redis_conn=None):
    close = False
    if redis_conn is None:
        redis_conn = redis.from_url(os.getenv("FM_REDIS_URI"))
        close = True

    queued_jobs = redis_conn.get("queued_jobs")
    if queued_jobs is None:
        return

    queued_jobs = json.loads(queued_jobs)

    jobs_source = queued_jobs.get(source)
    if jobs_source is None:
        return

    if job_id in jobs_source:
        jobs_source.remove(job_id)

    queued_jobs.update({source: jobs_source})
    redis_conn.set("queued_jobs", json.dumps(queued_jobs))

    if close:
        redis_conn.close()


def raise_error(detail, code=400):
    raise HTTPException(status_code=code, detail=detail)


def get_sherpa(x_api_key: str = Header(None)):
    if x_api_key is None:
        return None

    hashed_api_key = hashlib.sha256(x_api_key.encode("utf-8")).hexdigest()

    with DBSession() as dbsession:
        sherpa = dbsession.get_sherpa_with_hashed_api_key(hashed_api_key)
        sherpa_name = sherpa.name if sherpa else None

    return sherpa_name


def get_super_user(x_api_key: str = Header(None)):
    if x_api_key is None:
        return None

    hashed_api_key = hashlib.sha256(x_api_key.encode("utf-8")).hexdigest()

    with DBSession() as dbsession:
        super_user = dbsession.get_super_user_with_hashed_api_key(hashed_api_key)
        user_name = super_user.name if super_user else None

    return user_name


def get_user_from_header(x_user_token: str = Header(None)):
    if x_user_token is None:
        return None
    return decode_token(x_user_token)


def get_user_from_query(token: str = Query(None)):
    if token is None:
        return None
    return decode_token(token)


def get_real_ip_from_header(x_real_ip: str = Header(None)):
    return x_real_ip


def get_forwarded_for_from_header(x_forwarded_for: str = Header(None)):
    return x_forwarded_for


def decode_token(token: str):
    redis_conn = redis.from_url(os.getenv("FM_REDIS_URI"))
    try:
        details = jwt.decode(
            token,
            redis_conn.get("FM_SECRET_TOKEN"),
            algorithms=["HS256"],
            options={"require": ["exp", "sub"]},
        )
        return details["sub"]

    except jwt.exceptions.InvalidTokenError:
        return None


def generate_jwt_token(username: str, role=None, expiry_interval=None):
    redis_conn = redis.from_url(os.getenv("FM_REDIS_URI"))
    if expiry_interval is None:
        expiry_interval = int(redis_conn.get("token_expiry_time_sec").decode())
    access_token = jwt.encode(
        {
            "sub": username,
            "role": role,
            "exp": time.time() + expiry_interval,
        },
        redis_conn.get("FM_SECRET_TOKEN"),
        algorithm="HS256",
    )
    return access_token


async def check_token_expiry(token, client_ip, check_freq=30):
    while True:
        valid_user = decode_token(token)
        if valid_user is None:
            raise Exception(f"User token expired for {client_ip}")
        await asyncio.sleep(check_freq)


# processes the requests in the job queue.
def process_req(queue, req, user, redis_conn=None, dt=None):
    if not user:
        raise HTTPException(status_code=403, detail=f"Unknown requester {user}")

    if redis_conn is None:
        redis_conn = redis.from_url(os.getenv("FM_REDIS_URI"))

    job = None
    req.source = user

    handler_obj = hc.HandlerConfiguration.get_handler()
    args = [handler_obj, req]
    kwargs = {}

    default_job_timeout = int(int(redis_conn.get("default_job_timeout_ms").decode()) / 1000)
    generic_handler_job_timeout = int(
        int(redis_conn.get("generic_handler_job_timeout_ms").decode()) / 1000
    )

    ttl = req.ttl
    if ttl:
        kwargs.update({"ttl": ttl})

    timeout = default_job_timeout
    if not queue:
        queue = Queues.queues_dict["generic_handler"]
        timeout = generic_handler_job_timeout

    kwargs.update({"job_timeout": timeout})

    if dt:
        job = enqueue_at(queue, dt, handle, *args, **kwargs)
        return job

    job = enqueue(queue, handle, *args, **kwargs)

    return job


def relay_error_details(e: Exception):
    error_detail = "Unable to process request"
    status_code = 500
    if isinstance(e, ValueError):
        # request conflicts with the current state of the server.
        status_code = 409
        error_detail = str(e)

    elif isinstance(e, Exception):
        status_code = 400
        error_detail = str(e)
    raise_error(detail=error_detail, code=status_code)


async def process_req_with_response(queue, req, user: str):
    redis_conn = redis.from_url(os.getenv("FM_REDIS_URI"))
    job = process_req(queue, req, user, redis_conn)
    add_job_to_queued_jobs(job.id, req.source, redis_conn)

    status = ""
    while status not in ["finished", "failed"]:
        job = Job.fetch(job.id, connection=redis_conn)
        job.refresh()
        status = job.get_status()
        logging.debug(f"Job id: {Job.id}, Job status: {status}")
        await asyncio.sleep(0.01)

    remove_job_from_queued_jobs(job.id, req.source, redis_conn)

    if status == "failed":
        await asyncio.sleep(0.1)
        job_meta = job.get_meta(refresh=True)
        error_value = job_meta.get("error_value")
        job.cancel()
        relay_error_details(error_value)

    # Fetching the job result
    response = job.result
    if response is None:
        job = Job.fetch(job.id, connection=redis_conn)
        job.refresh()
        response = job.result
        logging.getLogger("fm_debug").warning(
            f"Got a null response from rq initially, req: {req}, new_response after refesh {response}"
        )

    return response


def handle(handler, msg, **kwargs):
    return handler.handle(msg)
