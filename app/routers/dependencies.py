import hashlib

from core.db import session_maker
from fastapi import Header
from models.fleet_models import Sherpa


def get_sherpa(x_api_key: str = Header(None)):
    if x_api_key is None:
        return None
    db = session_maker()
    hashed_api_key = hashlib.sha256(x_api_key.encode("utf-8")).hexdigest()
    db_sherpa: Sherpa = (
        db.query(Sherpa).filter(Sherpa.hashed_api_key == hashed_api_key).one_or_none()
    )
    return db_sherpa.name if db_sherpa else None
