import hashlib
import time
import jwt
from fastapi import HTTPException
from core.settings import settings
from fastapi import Depends, Header
from fastapi.param_functions import Query
from models.db_session import DBSession
from rq.job import Job
from utils.rq import enqueue, Queues
from core.config import Config
import redis
import os
import json
from models.request_models import SherpaReq


def get_db_session():
    session = DBSession()
    try:
        yield session
    finally:
        session.close()


def get_sherpa(x_api_key: str = Header(None), session=Depends(get_db_session)):
    if x_api_key is None:
        return None

    hashed_api_key = hashlib.sha256(x_api_key.encode("utf-8")).hexdigest()
    sherpa = session.get_sherpa_by_api_key(hashed_api_key)
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


def decode_token(token: str):
    try:
        details = jwt.decode(
            token,
            settings.FM_SECRET_KEY,
            algorithms=["HS256"],
            options={"require": ["exp", "sub"]},
        )
        return details["sub"]

    except jwt.exceptions.InvalidTokenError:
        return None


def generate_jwt_token(username: str):
    access_token = jwt.encode(
        {"sub": username, "exp": time.time() + 64800},
        settings.FM_SECRET_KEY,
        algorithm="HS256",
    )
    return access_token


def process_req(queue, req, user):

    if not user:
        raise HTTPException(status_code=403, detail=f"Unknown requeter {user}")

    if isinstance(req, SherpaReq):
        req.source = user

    handler_obj = Config.get_handler()

    if not queue:
        queue = Queues.queues_dict["generic_handler"]

    return enqueue(queue, handle, handler_obj, req)


def process_req_with_response(queue, req, user: str):
    job: Job = process_req(queue, req, user)
    redis_conn = redis.from_url(os.getenv("FM_REDIS_URI"))

    while True:
        status = Job.fetch(job.id, connection=redis_conn).get_status(refresh=True)

        if status == "finished":
            response = Job.fetch(job.id, connection=redis_conn).result
            break

        if status == "failed":

            # for recovery
            rq_fails = redis_conn.get("rq_fails")
            if not rq_fails:
                rq_fails = b"[]"

            rq_fails = json.loads(rq_fails)
            rq_fails.append([user, req.__dict__])
            redis_conn.set("rq_fails", json.dumps(rq_fails))

            raise HTTPException(status_code=500, detail="rq job failed")

        time.sleep(0.01)

    return response


def handle(handler, msg):
    return handler.handle(msg)
