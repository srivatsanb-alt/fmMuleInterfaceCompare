import hashlib
from fastapi import APIRouter

# ati code imports
import app.routers.dependencies as dpd
from models.db_session import DBSession
from models.request_models import UserLogin

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
    with DBSession() as dbsession:
        user = dbsession.get_frontend_user(user_login.name, hashed_password)
        if user is None:
            dpd.raise_error("Unknown requester", 401)

        response = {
            "access_token": dpd.generate_jwt_token(user_login.name),
            "user_details": {"user_name": user_login.name, "role": user.role},
        }

    return response
