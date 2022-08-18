from fastapi import APIRouter
from core.config import Config

from models.request_models import BookingReq, TripsReq
from utils.rq import Queues, enqueue


router = APIRouter(
    prefix="/api/v1/trips",
    tags=["trips"],
    responses={404: {"description": "Not found"}},
)


def process_req(req: TripsReq):
    handler_obj = Config.get_handler()
    enqueue(Queues.handler_queue, handle, handler_obj, req)


@router.post("/book/")
async def book(booking_req: BookingReq):
    process_req(booking_req)


def handle(handler, msg):
    handler.handle(msg)
