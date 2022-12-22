import hashlib
from app.routers.dependencies import (
    generate_jwt_token,
    close_session,
    close_session_and_raise_error,
)
from models.db_session import session
from fastapi import APIRouter
from models.request_models import UserLogin

router = APIRouter(
    prefix="/api/v1/user",
    tags=["auth"],
    responses={404: {"description": "Not found"}},
)


@router.post("/login")
async def login(user_login: UserLogin):

    hashed_password = hashlib.sha256(user_login.password.encode("utf-8")).hexdigest()

    user = session.get_frontend_user(user_login.name, hashed_password)
    if user is None:
        close_session_and_raise_error(session, "Unknown requester")
    role = "admin"
    response = {
        "access_token": generate_jwt_token(user_login.name),
        "user_details": {"user_name": user_login.name, "role": role},
    }

    close_session(session)
    return response
