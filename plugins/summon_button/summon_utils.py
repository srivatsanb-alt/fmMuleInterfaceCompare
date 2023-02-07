import os
import json
from plugins.plugin_comms import send_req_to_FM
import logging
import hashlib
from .summon_models import DBSession, SummonInfo, SummonAction
from models.trip_models import COMPLETED_TRIP_STATUS

logger_name = "plugin_summon_button"


def book_trip(dbsession, summon_info, route=[], plugin_name="plugin_summon_button"):
    endpoint = "trip_book"

    # always booking with 0 totes, num totes will be decided at the time of dispatch
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
        return

    for trip_id, trip_details in trip_book_response.items():
        trip = SummonAction(summon_id=summon_info.id, action=summon_info.press)
        dbsession.session.add(trip)
        summon_info.booking_id = trip_details["booking_id"]
        summon_info.trip_id = trip_id


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
                summon_info.station = summon_details["station"]
            else:

                summon_info = SummonInfo(
                    hashed_api_key=hashed_api_key,
                    press=summon_details["press"],
                    route=summon_details["route"],
                    station=summon_details["station"],
                    trip_id=None,
                    booking_id=None,
                )
                dbsession.session.add(summon_info)

        dbsession.session.commit()
