import hashlib
import os
import redis
import logging
from fastapi import APIRouter, Depends

# ati code imports
import app.routers.dependencies as dpd
import models.request_models as rqm
from models.mongo_client import FMMongo
from models.db_session import DBSession
import models.misc_models as mm
import utils.util as utils_util
import utils.config_utils as cu


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

        if user_login.name == cu.DefaultFrontendUser.admin["name"]:
            if hashed_password == cu.DefaultFrontendUser.admin["hashed_password"]:
                with DBSession() as dbsession:
                    default_password_log = f"Please change password for user: {user_login.name}, reason: weak password"
                    utils_util.maybe_add_notification(
                        dbsession,
                        dbsession.get_customer_names(),
                        default_password_log,
                        mm.NotificationLevels.alert,
                        mm.NotificationModules.generic,
                    )

    return response


@router.get("/plugin/{plugin_api_key}")
async def share_secrets_to_plugin(
    plugin_api_key: str,
):
    response = {}
    with FMMongo() as fm_mongo:
        hashed_api_key = hashlib.sha256(plugin_api_key.encode("utf-8")).hexdigest()
        hashed_api_key_db = fm_mongo.get_hashed_plugin_api_key()

        if hashed_api_key_db != hashed_api_key:
            dpd.raise_error("Unknown requester", 401)

        redis_conn = redis.from_url(os.getenv("FM_REDIS_URI"))
        response["FM_SECRET_TOKEN"] = redis_conn.get("FM_SECRET_TOKEN")

    return response


@router.post("/add_edit_frontend_user_details")
async def add_edit_user_details(
    frontend_user_details: rqm.FrontendUserDetails,
    user_name=Depends(dpd.get_user_from_header),
):
    response = {}

    if user_name is None:
        dpd.raise_error("Unknown requester", 401)

    default_admin_username = cu.DefaultFrontendUser.admin["name"]

    with FMMongo() as fm_mongo:
        operating_user_query = {"name": user_name}
        operating_user_details = fm_mongo.get_frontend_user_details(operating_user_query)
        operating_user_role = operating_user_details["role"]

        if getattr(rqm.FrontendUserRoles, operating_user_role) < getattr(
            rqm.FrontendUserRoles, frontend_user_details.role
        ):
            dpd.raise_error(
                f"{user_name}(role: {operating_user_role}) cannot add/edit an user with role: {frontend_user_details.role}"
            )

        user_query = {
            "name": frontend_user_details.name,
        }
        user_details_db = fm_mongo.get_frontend_user_details(user_query)
        db = fm_mongo.get_database("frontend_users")
        collection = fm_mongo.get_collection("user_details", db)

        if frontend_user_details.password is not None:
            if not utils_util.good_password_check(frontend_user_details.password):
                dpd.raise_error(
                    "Low password strenght: Password should contain atleast one upper case and one special character. Also the length should be greater than 8"
                )

        if user_details_db is None:
            if frontend_user_details.password is None:
                dpd.raise_error("Frontend user password cannot be None")
            temp = {
                "hashed_password": hashlib.sha256(
                    frontend_user_details.password.encode("utf-8")
                ).hexdigest(),
                "name": frontend_user_details.name,
                "role": frontend_user_details.role,
            }
            collection.insert_one(temp)
            logging.getLogger("configure_fleet").info(
                f"Inserted a new frontend user {frontend_user_details.name}"
            )
        else:
            if frontend_user_details.password is not None:
                user_details_db["hashed_password"] = hashlib.sha256(
                    frontend_user_details.password.encode("utf-8")
                ).hexdigest()

            if (
                frontend_user_details.name == default_admin_username
                and frontend_user_details.role != "support"
            ):
                dpd.raise_error(
                    f"Cannot change role for default frontend_user {default_admin_username}"
                )

            user_details_db["role"] = frontend_user_details.role
            collection.find_one_and_replace(user_query, user_details_db)
            logging.getLogger("configure_fleet").info(
                f"Modified frontend user details: {frontend_user_details.name}"
            )
    return response


@router.get("/delete_frontend_user/{frontend_user_name}")
async def delete_frontend_user(
    frontend_user_name: str,
    user_name=Depends(dpd.get_user_from_header),
):
    response = {}

    if user_name is None:
        dpd.raise_error("Unknown requester", 401)

    if frontend_user_name == cu.DefaultFrontendUser.admin["name"]:
        dpd.raise_error(f"Cannot delete default user: {frontend_user_name}")

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
