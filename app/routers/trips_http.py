from app.routers.dependencies import get_user_from_header
from core.config import Config
from fastapi import APIRouter, Depends, HTTPException
from models.request_models import BookingReq, TripsReq
from utils.rq import Queues, enqueue

router = APIRouter(
    prefix="/api/v1/trips",
    tags=["trips"],
    responses={404: {"description": "Not found"}},
)


def process_req(req: TripsReq, user: str):
    if not user:
        raise HTTPException(status_code=403, detail="Unknown user")

    handler_obj = Config.get_handler()
    enqueue(Queues.handler_queue, handle, handler_obj, req)


@router.post("/book/")
async def book(booking_req: BookingReq, user=Depends(get_user_from_header)):
    process_req(booking_req, user)


def handle(handler, msg):
    handler.handle(msg)
