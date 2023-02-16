import hashlib
from app.routers.dependencies import (
    generate_jwt_token,
    raise_error,
)
from fastapi import APIRouter

router = APIRouter(
    prefix="/api/v1/sanjaya",
    tags=["auth"],
    responses={404: {"description": "Not found"}},
)

# performs user authentication


@router.get("/check_connection")
async def check_connection():
    return {"uvicorn": "I am alive"}