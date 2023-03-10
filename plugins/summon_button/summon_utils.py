import os
import json
from plugins.plugin_comms import send_req_to_FM
import logging
import hashlib
from .summon_models import DBSession, SummonInfo,SummonActions
import time
from models.trip_models import COMPLETED_TRIP_STATUS
import redis
import secrets

logger_name = "plugin_summon_button"
logger = logging.getLogger(logger_name)

def get_station_info(station_name):
    status_code, response_json = send_req_to_FM(
        logger_name,
        "station_info",
        req_type="get",
        query=station_name,
    )
    return status_code,response_json

def gen_api_key(id: int) -> str:
    return secrets.token_urlsafe(32) + "_" + f'{id}'

def send_msg(msg):
        pub = redis.from_url(os.getenv("FM_REDIS_URI"), decode_responses=True)
        pub.publish("channel:plugin_summon_button", str(msg))

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
    send_req_to_FM(
        plugin_name, endpoint, req_type="delete", query=summon_info.booking_id,
    )
    summon_info.booking_id = None
    summon_info.trip_id = None
  
def send_job_updates_summon(color = "white"):
    while True:
        with DBSession() as dbsession:
            all_summon_buttons = dbsession.session.query(SummonInfo).all()

            
            for summon_button in all_summon_buttons:
                if summon_button.trip_id:
                    trip_ids = [summon_button.trip_id]
                    req_json = {"trip_ids": trip_ids}
                    status_code, trip_status_response = send_req_to_FM(
                        logger_name, "trip_status", req_type="post", req_json=req_json
                    )
                    for trip_id, trip_details in trip_status_response.items():
                        trip_status = trip_details["trip_details"]["status"]
                        logger.info(f"trip_id: {trip_id}, FM_response_status: {trip_status}")
                        if trip_status not in COMPLETED_TRIP_STATUS:
                            color = "green" 
                    msg = {"Led": color}
                    send_msg(msg)

        time.sleep(30)

# def populate_summon_info():
#     with DBSession() as dbsession:

        # api_key_summon_mapper = os.path.join(
        #     os.getenv("FM_MAP_DIR"),
        #     "plugin_summon_button",
        #     "api_key_summon_button_mapping.json",
        # )
        # with open(api_key_summon_mapper, "r") as f:
        #     api_key_summon_mapping = json.load(f)
        # for api_key, summon_details in api_key_summon_mapping.items():
        #     hashed_api_key = hashlib.sha256(api_key.encode("utf-8")).hexdigest()
        #     summon_info = (
        #         dbsession.session.query(SummonInfo)
        #         .filter(SummonInfo.hashed_api_key == hashed_api_key)
        #         .one_or_none()
        #     )
        #     if summon_info:
        #         summon_info.route = summon_details["route"]
        #         summon_info.press = summon_details["press"]
        #         # summon_info.station = summon_details["station"]
        #     else:

        #         summon_info = SummonInfo(
        #             hashed_api_key=hashed_api_key,
        #             press=summon_details["press"],
        #             route=summon_details["route"],
        #             station=None,
        #             trip_id=None,
        #             booking_id=None,
        #         )
        #         dbsession.session.add(summon_info)

        # dbsession.session.commit()


def add_edit_summon_info(
    dbsession: DBSession,
    id=None,
    api_key=None,
    route=None,
):
    summon_info: SummonInfo = (
        dbsession.session.query(SummonInfo)
        .filter(SummonInfo.id == id)
        .one_or_none()
    )
    logger.info(f"inside add or edit summon button:{summon_info}")
    if id is None:
        raise ValueError("Cannot add a summon button without id")

    if route:
        for station in route:
            status_code, response_json = get_station_info(station)
            if status_code!=200:
                ValueError("invalid station : {station}")

    if api_key is None:
        api_key = gen_api_key(id)
        logger.info(f"generated api_key {api_key}  for id {id}")

    hashed_api_key = hashlib.sha256(api_key.encode("utf-8")).hexdigest()

    if summon_info:
        summon_info.id = id
        summon_info.hashed_api_key = hashed_api_key
        summon_info.route = route
        summon_info.press = "book_trip"
    else:
        summon_info: SummonInfo = SummonInfo(
            id=id,
            hashed_api_key=hashed_api_key,
            route=route,
            press = "book_trip"
        )
        dbsession.session.add(summon_info)
        logger.info(
            f"added summon button {id}, with route: {route}"
        )
    dbsession.session.commit()
