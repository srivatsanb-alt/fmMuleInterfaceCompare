import hashlib
import os
from fastapi import APIRouter, Depends

# ati code imports
import app.routers.dependencies as dpd
import models.request_models as rqm
from models.mongo_client import FMMongo


router = APIRouter(
    prefix="/api/v1/user",
    tags=["auth"],
    responses={404: {"description": "Not found"}},
)

# performs user authentication


@router.post("/login")
async def login(user_login: rqm.UserLogin):
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


@router.post("/add_edit_frontend_user_details")
async def add_edit_user_details(
    frontend_user_details: rqm.FrontendUserDetails,
    user_name=Depends(dpd.get_user_from_header),
):
    response = {}

    if user_name is None:
        dpd.raise_error("Unknown requester", 401)

    with FMMongo() as fm_mongo:
        user_query = {
            "name": frontend_user_details.name,
        }
        user_details_db = fm_mongo.get_frontend_user_details(user_query)
        if user_details_db is None:
            db = fm_mongo.get_database("frontend_users")
            collection = fm_mongo.get_collection("user_details", db)
            temp = {
                "hashed_password": hashlib.sha256(
                    frontend_user_details.password.encode("utf-8")
                ).hexdigest(),
                "name": frontend_user_details.name,
                "role": frontend_user_details.role,
            }
            collection.insert_one(temp)
        else:
            user_details_db["hashed_password"] = hashlib.sha256(
                frontend_user_details.password.encode("utf-8")
            ).hexdigest()
            user_details_db["role"] = frontend_user_details.role

    return response


@router.get("/delete_frontend_user/{frontend_user_name}")
async def delete_frontend_user(
    frontend_user_name: str,
    user_name=Depends(dpd.get_user_from_header),
):
    response = {}

    if user_name is None:
        dpd.raise_error("Unknown requester", 401)

    with FMMongo() as fm_mongo:
        user_query = {
            "name": frontend_user_name,
        }
        user_details_db = fm_mongo.get_frontend_user_details(user_query)
        if user_details_db is None:
            dpd.raise_error("User not found")

        db = fm_mongo.get_database("frontend_users")
        collection = fm_mongo.get_collection("user_details", db)

        if collection.count_documents({}) > 1:
            collection.delete_one(user_query)
        else:
            dpd.raise_error("Cannot delete, atleat one user needs to exists")

    return response


@router.get("/get_all_frontend_users_info")
async def get_all_frontend_users(
    user_name=Depends(dpd.get_user_from_header),
):
    all_user_details = []

    if user_name is None:
        dpd.raise_error("Unknown requester", 401)

    with FMMongo() as fm_mongo:
        all_user_details = fm_mongo.get_all_frontend_users()

    return all_user_details
