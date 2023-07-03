from plugins.plugin_comms import send_req_to_FM, create_fm_notification
import logging
import hashlib
import secrets
import redis
import os
from .conveyor_models import DBSession, ConvInfo, ConvTrips
from models.trip_models import COMPLETED_TRIP_STATUS

logger_name = "plugin_conveyor"


def gen_api_key(name: str) -> str:
    return secrets.token_urlsafe(32) + "_" + name


def get_station_info(station_name):
    status_code, response_json = send_req_to_FM(
        "plugin_conveyor",
        "station_info",
        req_type="get",
        query=station_name,
    )
    return status_code, response_json


def book_trip(dbsession, route, plugin_name):
    endpoint = "trip_book"

    # always booking with 0 totes, num totes will be decided at the time of dispatch
    trip = {
        "route": route,
        "priority": 1,
        "metadata": {"conveyor_ops": "true", "num_units": "0"},
    }
    req_json = {"trips": [trip]}
    status_code, trip_book_response = send_req_to_FM(
        plugin_name, endpoint, req_type="post", req_json=req_json
    )

    if trip_book_response is None:
        raise ValueError("Trip booking failed")
        return

    for trip_id, trip_details in trip_book_response.items():
        trip = ConvTrips(
            booking_id=trip_details["booking_id"],
            trip_id=trip_id,
            route=route,
            active=True,
        )
        dbsession.session.add(trip)


def has_sherpa_passed_conveyor(trip_id, conveyor_name, plugin_name):
    req_json = {"trip_ids": [trip_id]}
    status_code, trip_status_response = send_req_to_FM(
        plugin_name, "trip_status", req_type="post", req_json=req_json
    )
    if trip_status_response:
        for trip_id, trip_status in trip_status_response.items():
            trip_details = trip_status["trip_details"]
            next_idx_aug = trip_details["next_idx_aug"]
            status = trip_details["status"]

            # trip is cancelled, failed, succeeded
            if status in COMPLETED_TRIP_STATUS:
                return True

            # Not an ongoing trip
            if next_idx_aug is None:
                return False

            # check for trips in progress
            route = trip_details["route"]
            if next_idx_aug > route.index(conveyor_name):
                return True

    return False


def get_tote_trip_info(dbsession, num_totes, conveyor_name, plugin_name):
    MAX_TOTE_PER_TRIP = 2
    incomplete_trips = (
        dbsession.session.query(ConvTrips).filter(ConvTrips.active.is_(True)).all()
    )
    epsilon = 1e-6
    num_trips = 0
    for trip in incomplete_trips:
        if conveyor_name not in trip.route:
            continue
        if not has_sherpa_passed_conveyor(trip.trip_id, conveyor_name, plugin_name):
            num_trips += 1
        else:
            trip.active = False

    book_trip = (num_totes / (num_trips + epsilon)) > MAX_TOTE_PER_TRIP
    return {"num_trips": num_trips, "num_totes": num_totes, "book_trip": book_trip}


def get_all_conveyors():
    all_conveyors = []
    with DBSession() as dbsession:
        all_conv_info = dbsession.session.query(ConvInfo).all()
        for conv_info in all_conv_info:
            all_conveyors.append(conv_info.name)

    return all_conveyors


def add_edit_conv(
    dbsession: DBSession, api_key=None, conveyor_name=None, nearest_chute=None
):

    if conveyor_name:
        status_code, conveyor_details = get_station_info(conveyor_name)
        if status_code != 200:
            raise ValueError(
                f"cannot add {conveyor_name} as conveyor, reason: invalid station"
            )
    if nearest_chute:
        status_code, conveyor_details = get_station_info(nearest_chute)
        if status_code != 200:
            raise ValueError(f"Invalid nearest_chute entry, reason: invalid station")

    conv_info: ConvInfo = (
        dbsession.session.query(ConvInfo)
        .filter(ConvInfo.name == conveyor_name)
        .one_or_none()
    )

    if api_key is None:
        if not conv_info:
            api_key = gen_api_key(conveyor_name)
            logging.getLogger(logger_name).info(
                f"generated api_key {api_key}  for conveyor name: {conveyor_name}"
            )
            hashed_api_key = hashlib.sha256(api_key.encode("utf-8")).hexdigest()
    else:
        hashed_api_key = hashlib.sha256(api_key.encode("utf-8")).hexdigest()

    if conv_info:
        conv_info.name = conveyor_name
        if api_key:
            conv_info.hashed_api_key = hashed_api_key
        conv_info.nearest_chute = nearest_chute
    else:
        conv_info: ConvInfo = ConvInfo(
            name=conveyor_name,
            hashed_api_key=hashed_api_key,
            num_totes=0,
            nearest_chute=nearest_chute,
            fleet_name=conveyor_details["fleet_name"],
        )
        dbsession.session.add(conv_info)
        create_fm_notification(
            "plugin_conveyor",
            f"Please restart fleet manager new conveyor: {conveyor_name} has been added",
        )
        logging.getLogger(logger_name).info(
            f"added conveyor info with api_key {api_key}, with station name: {conveyor_name}"
        )


def send_msg_to_conveyor(msg, conveyor_name):
    pub = redis.from_url(os.getenv("FM_REDIS_URI"), decode_responses=True)
    pub.publish(f"channel:plugin_conveyor_{conveyor_name}", str(msg))


def close_conveyor_ws(conveyor_name):
    msg = "close_ws"
    send_msg_to_conveyor(msg, conveyor_name)
