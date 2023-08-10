import hashlib
import os
from fastapi import APIRouter

# ati code imports
import app.routers.dependencies as dpd
from models.request_models import UserLogin
from models.mongo_client import FMMongo

router = APIRouter(
    prefix="/api/v1/user",
    tags=["auth"],
    responses={404: {"description": "Not found"}},
)

# performs user authentication


@router.post("/login")
async def login(user_login: UserLogin):
    response = {}

    hashed_password = hashlib.sha256(user_login.password.encode("utf-8")).hexdigest()

    with FMMongo() as fm_mongo:
        user_query = {"name": user_login.name, "hashed_password": hashed_password}
        user_details = fm_mongo.get_frontend_user_details(user_query)
        if user_details is None:
            dpd.raise_error("Unknown requester", 401)

        response = {
            "access_token": dpd.generate_jwt_token(user_login.name),
            "user_details": {"user_name": user_login.name, "role": user_details["role"]},
            "static_files_auth": {
                "username": os.getenv("ATI_STATIC_AUTH_USERNAME"),
                "password": os.getenv("ATI_STATIC_AUTH_PASSWORD"),
            },
        }

    return response
