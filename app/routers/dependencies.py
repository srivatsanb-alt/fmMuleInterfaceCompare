import hashlib
from fastapi import Header
from models.db_session import session


def get_sherpa(x_api_key: str = Header(None)):
    if x_api_key is None:
        return None
    hashed_api_key = hashlib.sha256(x_api_key.encode("utf-8")).hexdigest()
    return session.get_sherpa_by_api_key(hashed_api_key)
