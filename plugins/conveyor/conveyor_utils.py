import os
import json
from plugins.plugin_comms import send_req_to_FM
import logging
import hashlib
from .conveyor_models import DBSession, ConvInfo, ConvTrips

logger_name = "plugin_conveyor"


def get_station_info(station_name):
    status_code, response_json = send_req_to_FM(
        "plugin_conveyor",
        "station_info",
        req_type="get",
        query=station_name,
    )
    return response_json


def book_trip(dbsession, route, plugin_name):
    endpoint = "trip_book"

    # always booking with 0 totes, num totes will be decided at the time of dispatch
    trip = {
        "route": route,
        "priority": 1,
        "metadata": {"conveyor_ops": True, "num_units": 0},
    }
    req_json = {"trips": [trip]}
    status_code, trip_book_response = send_req_to_FM(
        plugin_name, endpoint, req_type="post", req_json=req_json
    )

    if trip_book_response is None:
        return

    for trip_id, trip_details in trip_book_response.items():
        trip = ConvTrips(
            booking_id=trip_details["booking_id"],
            trip_id=trip_id,
            route=route,
            completed=False,
        )
        dbsession.session.add(trip)


def has_sherpa_passed_conveyor(trip_id, conveyor_name, plugin_name):
    req_json = {"trip_ids": [trip_id]}
    status_code, trip_status_response = send_req_to_FM(
        plugin_name, "trip_status", req_type="post", req_json=req_json
    )
    if trip_status_response:
        for trip_id, trip_details in trip_status_response.items():
            next_idx_aug = trip_details["next_idx_aug"]
            route = trip_details["route"]
            if route.index(conveyor_name) <= next_idx_aug:
                return True
    return False


def get_tote_trip_info(dbsession, num_totes, conveyor_name, plugin_name):
    MAX_TOTE_PER_TRIP = 2
    incomplete_trips = (
        dbsession.session.query(ConvTrips).filter(ConvTrips.active.is_(False)).all()
    )
    epsilon = 1e-6
    num_trips = 0
    for trip in incomplete_trips:
        if not has_sherpa_passed_conveyor(trip.trip_id, conveyor_name):
            num_trips += 1
        else:
            trip.active = False
    book_trip = (num_totes / (num_trips + epsilon)) > MAX_TOTE_PER_TRIP
    return {"num_trips": num_trips, "num_totes": num_totes, "book_trip": book_trip}


def populate_conv_info():
    all_conveyors = []
    with DBSession() as dbsession:
        api_key_conveyor_mapper = os.path.join(
            os.getenv("FM_MAP_DIR"), "plugin_conveyor", "api_key_conveyor_mapping.json"
        )
        with open(api_key_conveyor_mapper, "r") as f:
            api_key_conveyor_mapping = json.load(f)
        for api_key, conveyor_details in api_key_conveyor_mapping.items():
            conveyor_name = conveyor_details["name"]
            status_code, response_json = send_req_to_FM(
                "plugin_conveyor",
                "station_info",
                req_type="get",
                query=conveyor_name,
            )

            if response_json is not None:
                all_conveyors.append(conveyor_name)
                station_info = response_json
                # if StationProperties.CONVEYOR in station_info["properties"]:
                logging.getLogger(logger_name).info(f"Will add {conveyor_name} to DB")
                station_type = "conveyor"
                hashed_api_key = hashlib.sha256(api_key.encode("utf-8")).hexdigest()
                conv_info = (
                    dbsession.session.query(ConvInfo)
                    .filter(ConvInfo.name == conveyor_name)
                    .one_or_none()
                )
                if conv_info is None:
                    conv_info = ConvInfo(
                        name=conveyor_details["name"],
                        hashed_api_key=hashed_api_key,
                        num_totes=0,
                        type=station_type,
                        nearest_chute=conveyor_details["nearest_chute"],
                        fleet_name=station_info["fleet_name"],
                    )
                    dbsession.session.add(conv_info)
                else:
                    conv_info.nearest_chute = conv_info
                    conv_info.fleet_name = station_info["fleet_name"]

            dbsession.session.commit()

        return all_conveyors
