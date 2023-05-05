import os
import logging
import hashlib
import time
import redis
import secrets

# ati code imports
import models.trip_models as tm
from plugins.plugin_comms import send_req_to_FM
from .summon_models import DBSession, SummonInfo, SummonActions


logger_name = "plugin_summon_button"
logger = logging.getLogger(logger_name)


def get_station_info(station_name):
    status_code, response_json = send_req_to_FM(
        logger_name,
        "station_info",
        req_type="get",
        query=station_name,
    )
    return status_code, response_json


def gen_api_key(id: int) -> str:
    return secrets.token_urlsafe(32) + "_" + f"{id}"


def send_msg_to_summon_button(msg, unique_id):
    pub = redis.from_url(os.getenv("FM_REDIS_URI"), decode_responses=True)
    pub.publish(f"channel:plugin_summon_button_{unique_id}", str(msg))


def close_summon_button_ws(unique_id):
    msg = {"close_ws": True}
    pub = redis.from_url(os.getenv("FM_REDIS_URI"), decode_responses=True)
    pub.publish(f"channel:plugin_summon_button_{unique_id}", str(msg))


def book_trip(dbsession, summon_info, route=[], plugin_name=logger_name):
    endpoint = "trip_book"

    trip = {
        "route": route,
        "priority": 1,
    }
    req_json = {"trips": [trip]}
    status_code, trip_book_response = send_req_to_FM(
        plugin_name, endpoint, req_type="post", req_json=req_json
    )

    if trip_book_response is None:
        raise ValueError("Trip booking failed")

    for trip_id, trip_details in trip_book_response.items():
        trip = SummonActions(summon_id=summon_info.id, action=summon_info.press)
        dbsession.session.add(trip)
        summon_info.booking_id = trip_details["booking_id"]
        summon_info.trip_id = trip_id


def cancel_trip(dbsession, summon_info, plugin_name="plugin_summon_button"):
    endpoint = "delete_booked_trip"

    response_status_code, response_json = send_req_to_FM(
        plugin_name,
        endpoint,
        req_type="delete",
        query=summon_info.booking_id,
    )

    if response_status_code != 200:
        raise ValueError("Could not delete booked trip")

    summon_info.booking_id = None
    summon_info.trip_id = None


def send_job_updates_summon():
    while True:
        with DBSession() as dbsession:
            all_summon_buttons = dbsession.session.query(SummonInfo).all()
            summon_button_with_trips = (
                dbsession.session.query(SummonInfo.trip_id)
                .filter(SummonInfo.trip_id != None)
                .all()
            )
            trip_ids = []
            for trip_id in summon_button_with_trips:
                trip_ids.append(trip_id[0])

            if len(trip_ids):
                req_json = {"trip_ids": trip_ids}
                status_code, trip_status_response = send_req_to_FM(
                    logger_name, "trip_status", req_type="post", req_json=req_json
                )
            for summon_button in all_summon_buttons:
                color = "white"
                if summon_button.trip_id:
                    trip_details = trip_status_response.get(str(summon_button.trip_id))
                    trip_status = trip_details["trip_details"]["status"]
                    logger.info(f"trip_id: {trip_id}, FM_response_status: {trip_status}")
                    if trip_status == tm.TripStatus.SUCCEEDED:
                        summon_button.booking_id = None
                        summon_button.trip_id = None
                        color = "blinking green"
                    elif trip_status == tm.TripStatus.WAITING_STATION:
                        color = "blinking green"
                    elif trip_status in tm.YET_TO_START_TRIP_STATUS:
                        color = "rotating yellow"
                    elif trip_status == tm.TripStatus.EN_ROUTE:
                        color = "rotating green"
                    else:
                        summon_button.booking_id = None
                        summon_button.trip_id = None

                msg = {"Led": color}
                send_msg_to_summon_button(msg, summon_button.id)
        time.sleep(5)


def add_edit_summon_info(
    dbsession: DBSession, id=None, api_key=None, route=None, description=None
):

    summon_info: SummonInfo = (
        dbsession.session.query(SummonInfo).filter(SummonInfo.id == id).one_or_none()
    )

    if route:
        for station_name in route:
            status_code, response_json = get_station_info(station_name)
            if status_code != 200:
                ValueError(f"invalid station : {station_name}")

    if api_key is None:
        if not summon_info:
            api_key = gen_api_key(id)
            logger.info(
                f"generated api_key {api_key} for summon button with id {id}, description: {description}"
            )
            hashed_api_key = hashlib.sha256(api_key.encode("utf-8")).hexdigest()
    else:
        hashed_api_key = hashlib.sha256(api_key.encode("utf-8")).hexdigest()

    if summon_info:
        summon_info.id = id
        if api_key:
            summon_info.hashed_api_key = hashed_api_key
        summon_info.route = route
        summon_info.press = "book_trip"
        summon_info.description = description
    else:
        summon_info: SummonInfo = SummonInfo(
            hashed_api_key=hashed_api_key,
            route=route,
            press="book_trip",
            description=description,
        )
        dbsession.session.add(summon_info)
        logger.info(f"added summon button {id}, with route: {route}")
