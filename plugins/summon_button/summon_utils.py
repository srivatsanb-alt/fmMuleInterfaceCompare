import os
import json
from plugins.plugin_comms import send_req_to_FM
import logging
import hashlib
from .summon_models import DBSession, SummonInfo,SummonActions
import time
from models.trip_models import COMPLETED_TRIP_STATUS
import redis

logger_name = "plugin_summon_button"

def send_msg(msg):
        pub = redis.from_url(os.getenv("FM_REDIS_URI"), decode_responses=True)
        pub.publish("channel:plugin_summon_button", str(msg))

def book_trip(dbsession, summon_info, route=[], plugin_name="plugin_summon_button"):
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
    logger = logging.getLogger("plugin_summon_button")
    while True:
        with DBSession() as dbsession:
            all_summon_buttons = dbsession.session.query(SummonInfo).all()

            
            for summon_button in all_summon_buttons:
                if summon_button.trip_id:
                    trip_ids = [summon_button.trip_id]
                    req_json = {"trip_ids": trip_ids}
                    status_code, trip_status_response = send_req_to_FM(
                        "plugin_summon_button", "trip_status", req_type="post", req_json=req_json
                    )
                    for trip_id, trip_details in trip_status_response.items():
                        trip_status = trip_details["trip_details"]["status"]
                        logger.info(f"trip_id: {trip_id}, FM_response_status: {trip_status}")
                        if trip_status not in COMPLETED_TRIP_STATUS:
                            color = "green" 
                    msg = {"Led": color}
                    send_msg(msg)

        time.sleep(30)

def populate_summon_info():
    with DBSession() as dbsession:
        api_key_summon_mapper = os.path.join(
            os.getenv("FM_MAP_DIR"),
            "plugin_summon_button",
            "api_key_summon_button_mapping.json",
        )
        with open(api_key_summon_mapper, "r") as f:
            api_key_summon_mapping = json.load(f)
        for api_key, summon_details in api_key_summon_mapping.items():
            hashed_api_key = hashlib.sha256(api_key.encode("utf-8")).hexdigest()
            summon_info = (
                dbsession.session.query(SummonInfo)
                .filter(SummonInfo.hashed_api_key == hashed_api_key)
                .one_or_none()
            )
            if summon_info:
                summon_info.route = summon_details["route"]
                summon_info.press = summon_details["press"]
                # summon_info.station = summon_details["station"]
            else:

                summon_info = SummonInfo(
                    hashed_api_key=hashed_api_key,
                    press=summon_details["press"],
                    route=summon_details["route"],
                    station=None,
                    trip_id=None,
                    booking_id=None,
                )
                dbsession.session.add(summon_info)

        dbsession.session.commit()
