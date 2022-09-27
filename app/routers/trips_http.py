from app.routers.dependencies import get_user_from_header
from core.config import Config
from fastapi import APIRouter, Depends, HTTPException
from models.request_models import BookingReq, TripStatusReq, PauseResumeReq
from models.trip_models import Trip, OngoingTrip, PendingTrip, TripStatus
from utils.rq import Queues, enqueue
from fastapi.responses import HTMLResponse
from rq.job import Job
from models.db_session import session
import redis
import os
import time
import utils.trip_utils as tu
import pandas as pd

router = APIRouter(
    prefix="/api/v1/trips",
    tags=["trips"],
    responses={404: {"description": "Not found"}},
)


def process_req(req, user: str):
    if user is None:
        raise HTTPException(status_code=403, detail="Unknown requester")
    handler_obj = Config.get_handler()

    return enqueue(Queues.handler_queue, handle, handler_obj, req)


def process_req_with_response(req, user: str):
    response = {}
    job: Job = process_req(req, user)
    redis_conn = redis.from_url(os.getenv("FM_REDIS_URI"))
    n_attempt = 1
    while True:
        status = Job.fetch(job.id, connection=redis_conn).get_status(refresh=True)
        if status == "finished":
            response = Job.fetch(job.id, connection=redis_conn).result
            break
        if status == "failed":
            time.sleep(1)
            job: Job = process_req(req, user)
            RETRY_ATTEMPTS = Config.get_rq_job_params()["http_retry_attempts"]
            if n_attempt > RETRY_ATTEMPTS:
                raise HTTPException(status_code=403, detail="rq job failed multiple times")
            n_attempt = n_attempt + 1
        time.sleep(0.1)
    return response


@router.post("/book/")
async def book(booking_req: BookingReq, user_name=Depends(get_user_from_header)):

    response = process_req_with_response(booking_req, user_name)
    return response


@router.delete("/booking/{booking_id}")
async def delete_pending_trip(booking_id: int, user_name=Depends(get_user_from_header)):

    if not user_name:
        raise HTTPException(status_code=403, detail="Unknown requester")

    response = {}
    trips = session.get_trip_with_booking_id(booking_id)

    if not trips:
        raise HTTPException(status_code=403, detail="no trip with the given booking_id")

    for trip in trips:
        if trip.status != TripStatus.BOOKED:
            raise HTTPException(status_code=403, detail="expected trip status to be booked")

        pending_trip: PendingTrip = session.get_pending_trip_with_trip_id(trip.id)
        session.delete_pending_trip(pending_trip)
        session.close()

    return response


@router.delete("/ongoing/{booking_id}")
async def delete_ongoing_trip(booking_id: int, user_name=Depends(get_user_from_header)):

    if not user_name:
        raise HTTPException(status_code=403, detail="Unknown requester")

    response = {}
    trips = session.get_trip_with_booking_id(booking_id)

    if not trips:
        raise HTTPException(status_code=403, detail="no trip with the given booking_id")

    for trip in trips:
        if trip.status != TripStatus.EN_ROUTE:
            raise HTTPException(
                status_code=403, detail="expected trip status to be enroute"
            )

        ongoing_trip: OngoingTrip = session.get_ongoing_trip_with_trip_id(trip.id)
        sherpa_name = ongoing_trip.sherpa_name
        session.delete_ongoing_trip(ongoing_trip)
        pause_resume_req = PauseResumeReq(pause=True, sherpa_name=sherpa_name)
        _ = process_req_with_response(pause_resume_req, user_name)

    return response


@router.get("/status/{num_trips}/{viewable}")
def get_last_n_trip_status(num_trips: int, viewable: int):
    response = {}
    trips = session.get_last_n_trips(num_trips)
    trip_ids = [trip.id for trip in trips]

    if not trip_ids:
        raise HTTPException(status_code=403, detail="bad request no trip id")

    for trip_id in trip_ids:
        trip: Trip = session.get_trip(trip_id)
        if not trip:
            raise HTTPException(status_code=403, detail="invalid trip id")

        response.update({trip_id: tu.get_trip_status(trip)})

    # temporary addition for first release
    # TODO : remove viewable code after frontend is enabled to read trips table
    if viewable:
        df = pd.DataFrame(data=response)
        df = df.fillna(" ")
        response = df.to_html()
        return HTMLResponse(content=response, status_code=200)

    return response


@router.post("/status")
async def trip_status(
    trip_status_req: TripStatusReq, user_name=Depends(get_user_from_header)
):
    if not user_name:
        raise HTTPException(status_code=403, detail="Unknown requester")

    response = {}
    # if trip_status_req.booked_from and trip_status_req.booked_till:
    #     # trip_ids = session.get_trip_ids_with_timestamp(
    #     #     trip_status_req.booked_from, trip_status_req.booked_till
    #     # )
    #     # trip_status_req.trip_ids = trip_ids
    #     #
    #     # if not trip_ids:
    #     #     raise HTTPException(status_code=403, detail="no trip in the given timeframe")

    if not trip_status_req.trip_ids:
        raise HTTPException(status_code=403, detail="bad request no trip id")

    for trip_id in trip_status_req.trip_ids:

        trip: Trip = session.get_trip(trip_id)
        if not trip:
            raise HTTPException(status_code=403, detail="invalid trip id")

        response.update({trip_id: tu.get_trip_status(trip)})

    return response


def handle(handler, msg):
    handler.handle(msg)
