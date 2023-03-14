import os
import redis
import jwt
from fastapi import HTTPException
from fastapi import Header
from fastapi.param_functions import Query


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
