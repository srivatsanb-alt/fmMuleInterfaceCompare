import hashlib
import time
import jwt
from fastapi import HTTPException
import logging
from fastapi import Header
from fastapi.param_functions import Query
from rq.job import Job
from rq import Retry
from utils.rq import enqueue, enqueue_at, Queues
from core.config import Config
import redis
import os
from models.request_models import SherpaReq
from models.db_session import DBSession


def raise_error(detail):
    raise HTTPException(status_code=403, detail=detail)


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


def process_req(queue, req, user, dt=None):

    if not user:
        raise HTTPException(status_code=403, detail=f"Unknown requeter {user}")

    req.source = user

    handler_obj = Config.get_handler()
    args = [handler_obj, req]
    kwargs = {}

    if not queue:
        # generic handler - is high priority queue - cannot wait for default timeout(180 seconds)
        kwargs.update({"job_timeout": 30})
        queue = Queues.queues_dict["generic_handler"]

    # add retry only for SherpaReq(req comes from Sherpa)
    if isinstance(req, SherpaReq):
        kwargs.update({"retry": Retry(max=3, interval=[0.5, 1, 2])})

    if dt:
        return enqueue_at(queue, dt, handle, *args, **kwargs)

    return enqueue(queue, handle, *args, **kwargs)


def process_req_with_response(queue, req, user: str):
    job: Job = process_req(queue, req, user)
    redis_conn = redis.from_url(os.getenv("FM_REDIS_URI"))

    while True:
        job = Job.fetch(job.id, connection=redis_conn)
        status = job.get_status(refresh=True)

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
