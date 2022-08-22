import hashlib
import time
import jwt
import secrets
from fastapi import Header
from models.db_session import session
from models.fleet_models import Sherpa
from fastapi.param_functions import Query
from core.settings import settings


def get_sherpa(x_api_key: str = Header(None)):
    if x_api_key is None:
        return None

    hashed_api_key = hashlib.sha256(x_api_key.encode("utf-8")).hexdigest()
    sherpa = session.get_sherpa_by_api_key(hashed_api_key)
    sherpa_name = sherpa.name if sherpa else None
    session.close()

    return sherpa_name


def get_frontend_user(
    token: str = Query(None)
):

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
