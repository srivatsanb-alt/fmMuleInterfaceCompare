import hashlib
import time
import jwt
from fastapi import HTTPException
from fastapi import Header
from fastapi.param_functions import Query
from rq.job import Job
from rq import Retry
from utils.rq_utils import enqueue, enqueue_at, Queues
from core.config import Config
import redis
import os
import json
from models.request_models import SherpaReq
from models.db_session import DBSession


def add_job_to_queued_jobs(job_id, source):
    redis_conn = redis.from_url(os.getenv("FM_REDIS_URI"))
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
    redis_conn.close()


def remove_job_from_queued_jobs(job_id, source):
    redis_conn = redis.from_url(os.getenv("FM_REDIS_URI"))
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
    redis_conn.close()


def raise_error(detail, code=400):
    raise HTTPException(status_code=code, detail=detail)


def get_sherpa(x_api_key: str = Header(None)):
    if x_api_key is None:
        return None

    hashed_api_key = hashlib.sha256(x_api_key.encode("utf-8")).hexdigest()

    with DBSession() as dbsession:
        sherpa = dbsession.get_sherpa_by_api_key(hashed_api_key)
        sherpa_name = sherpa.name if sherpa else None

    return sherpa_name


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


def generate_jwt_token(username: str):
    redis_conn = redis.from_url(os.getenv("FM_REDIS_URI"))
    access_token = jwt.encode(
        {"sub": username, "exp": time.time() + 64800},
        redis_conn.get("FM_SECRET_TOKEN"),
        algorithm="HS256",
    )
    return access_token


def process_req(queue, req, user, dt=None, ttl=None):

    if not user:
        raise HTTPException(status_code=403, detail=f"Unknown requeter {user}")

    rq_params = Config.get_fleet_rq_params()

    job = None

    req.source = user

    handler_obj = Config.get_handler()
    args = [handler_obj, req]
    kwargs = {}

    job_timeout = rq_params.get("default_job_timeout", 15)
    kwargs.update({"job_timeout": job_timeout})

    if ttl:
        kwargs.update({"ttl": ttl})

    if not queue:
        # generic handler - is high priority queue - cannot wait for default timeout(180 seconds)
        job_timeout = rq_params.get("generic_handler_job_timeout", 10)
        kwargs.update({"job_timeout": job_timeout})
        queue = Queues.queues_dict["generic_handler"]

    # add retry only for SherpaReq(req comes from Sherpa)
    if isinstance(req, SherpaReq):
        kwargs.update({"retry": Retry(max=3, interval=[0.5, 1, 2])})

    if dt:
        job = enqueue_at(queue, dt, handle, *args, **kwargs)
        return job

    job = enqueue(queue, handle, *args, **kwargs)
    return job


def process_req_with_response(queue, req, user: str):
    job: Job = process_req(queue, req, user)
    add_job_to_queued_jobs(job.id, req.source)

    redis_conn = redis.from_url(os.getenv("FM_REDIS_URI"))

    while True:
        job = Job.fetch(job.id, connection=redis_conn)
        status = job.get_status(refresh=True)

        if status in ["finished", "failed"]:
            remove_job_from_queued_jobs(job.id, req.source)

        if status == "finished":
            response = job.result
            break
        if status == "failed":
            job.cancel()
            raise HTTPException(status_code=500, detail="Unable to process the request")

        time.sleep(0.01)

    return response


def handle(handler, msg):
    return handler.handle(msg)
