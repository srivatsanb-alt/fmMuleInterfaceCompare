import os
import time
import redis
from app.routers.dependencies import get_user_from_header
from core.config import Config
from models.request_models import (
    FleetInfoRequest
)
from models.db_session import session
from fastapi import APIRouter, Depends, HTTPException

router = APIRouter(
    responses={404: {"description": "Not found"}},
)
