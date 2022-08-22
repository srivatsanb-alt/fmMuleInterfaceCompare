import os
import time
import redis
import hashlib
from fastapi import APIRouter, Depends, HTTPException
from models.request_models import FrontendUserLogin
from models.db_session import session
from app.routers.dependencies import generate_jwt_token
from rq.job import Job


router = APIRouter(prefix="/api/v1/frontend",
                   tags=["frontend"],
                   responses={404: {"description": "Not found"}})


@router.post("/login")
async def login(user_login: FrontendUserLogin):

    hashed_password = hashlib.sha256(
                        user_login.password.encode("utf-8")).hexdigest()

    user = session.get_frontend_user(user_login.name, hashed_password)
    if user is None:
        raise HTTPException(status_code=403, detail="Unknown requester")

    response = {
        "access_token":  generate_jwt_token(user_login.name)
    }

    return response
