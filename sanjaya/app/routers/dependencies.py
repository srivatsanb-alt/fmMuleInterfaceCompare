import time
import jwt
from fastapi import HTTPException
from fastapi import Header
from fastapi.param_functions import Query
import redis
import os
import json


# upon assignment of a task, it gets added into the job queue
def add_job_to_queued_jobs(job_id, source):
    redis_conn = redis.from_url(os.getenv("REDIS_URI"))
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


# removes job from the job queue


def remove_job_from_queued_jobs(job_id, source):
    redis_conn = redis.from_url(os.getenv("REDIS_URI"))
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
    redis_conn = redis.from_url(os.getenv("REDIS_URI"))
    try:
        details = jwt.decode(
            token,
            redis_conn.get("SECRET_TOKEN"),
            algorithms=["HS256"],
            options={"require": ["exp", "sub"]},
        )
        return details["sub"]

    except jwt.exceptions.InvalidTokenError:
        return None


def generate_jwt_token(username: str):
    redis_conn = redis.from_url(os.getenv("REDIS_URI"))
    access_token = jwt.encode(
        {"sub": username, "exp": time.time() + 64800},
        redis_conn.get("SECRET_TOKEN"),
        algorithm="HS256",
    )
    return access_token
