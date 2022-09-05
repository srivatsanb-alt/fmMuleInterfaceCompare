import hashlib

from app.routers.dependencies import generate_jwt_token, get_db_session
from fastapi import APIRouter, Depends, HTTPException
from models.request_models import UserLogin

router = APIRouter(
    prefix="/api/v1/user",
    tags=["auth"],
    responses={404: {"description": "Not found"}},
)


@router.post("/login")
async def login(user_login: UserLogin, session=Depends(get_db_session)):

    hashed_password = hashlib.sha256(user_login.password.encode("utf-8")).hexdigest()

    user = session.get_frontend_user(user_login.name, hashed_password)
    if user is None:
        raise HTTPException(status_code=403, detail="Unknown requester")

    role = "admin"
    response = {
        "access_token": generate_jwt_token(user_login.name),
        "user_details": {"user_name": user_login.name, "role": role},
    }

    return response
