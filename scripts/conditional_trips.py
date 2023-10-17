# python module imports
import datetime
import time
import logging
from sqlalchemy.sql import not_
from sqlalchemy import any_

# ati code imports
from models.db_session import DBSession
from models.mongo_client import FMMongo
import models.trip_models as tm
import models.fleet_models as fm
import models.request_models as rqm
import app.routers.dependencies as dpd


def get_conditional_trip_config():

    with FMMongo() as fm_mongo:
        conditional_trips_config = fm_mongo.get_document_from_fm_config("conditional_trips")

    return conditional_trips_config


def enqueue_trip_msg(sherpa_name: str, route: list, trip_type: str, priority: float):
    trip_metadata = {
        "sherpa_name": sherpa_name,
        "conditional": str(True),
        "trip_type": trip_type,
    }
    conditional_booking_req: rqm.BookingReq = rqm.BookingReq(
        trips=[rqm.TripMsg(route=route, priority=priority, metadata=trip_metadata)]
    )
    dpd.process_req(None, conditional_booking_req, f"{trip_type}_{sherpa_name}")


class BookConditionalTrip:
    def __init__(self, dbsession, trip_types, config):
        self.dbsession = dbsession
        self.trip_types = trip_types
        self.config = config

    def book_trip(self, trip_type):
        book_fn = getattr(self, f"book_{trip_type}_trips", None)
        if book_fn is None:
            logging.getLogger("misc").info(f"Invalid conditional trip type {trip_type}")
            return

        config = self.config.get(trip_type)
        if config["book"]:
            book_fn(config, trip_type)
            time.sleep(5)
        else:
            logging.getLogger("misc").info(f"Will not book {trip_type} trips")

    def is_station_already_booked_with_conditional_trip(self, trip_type, station_name):
        temp = (
            self.dbsession.session.query(tm.Trip)
            .filter(tm.Trip.booked_by.like(f"{trip_type}%"))
            .filter(any_(tm.Trip.route) == station_name)
            .filter(not_(tm.Trip.status.in_(tm.COMPLETED_TRIP_STATUS)))
            .all()
        )
        if len(temp) > 0:
            return True
        return False

    def get_low_battery_sherpa_status(self, threshold: int):
        return (
            self.dbsession.session.query(fm.SherpaStatus)
            .filter(fm.SherpaStatus.battery_status < threshold)
            .filter(fm.SherpaStatus.battery_status != -1)
            .filter(not_(fm.SherpaStatus.disabled.is_(True)))
            .filter(fm.SherpaStatus.mode == "fleet")
            .order_by(fm.SherpaStatus.battery_status)
            .all()
        )

    def get_idling_sherpa_status(self, threshold: int):
        temp = (
            self.dbsession.session.query(fm.SherpaStatus)
            .filter(fm.SherpaStatus.trip_id == None)
            .filter(not_(fm.SherpaStatus.disabled.is_(True)))
            .filter(fm.SherpaStatus.mode == "fleet")
            .filter(fm.SherpaStatus.inducted.is_(True))
            .all()
        )

        idling_sherpa_status = []

        for sherpa_status in temp:
            today_now = datetime.datetime.now()
            sherpa_name = sherpa_status.sherpa_name
            last_trip = self.dbsession.get_last_trip(sherpa_name)

            if last_trip is None:
                continue

            if last_trip.end_time is None:
                continue

            if (today_now - last_trip.end_time).seconds > threshold:
                logging.getLogger("misc").warning(f"{sherpa_name} has been found idling")
                idling_sherpa_status.append(sherpa_status)

        return idling_sherpa_status

    def is_trip_already_booked(self, sherpa_name: str, current_trip_type: str):
        """
        not checking current trip type
        book only one conditional trip at a time
        """
        all_trip_types = [f"{trip_type}_{sherpa_name}" for trip_type in self.trip_types]
        trips = (
            self.dbsession.session.query(tm.Trip)
            .filter(tm.Trip.booked_by.in_(all_trip_types))
            .filter(not_(tm.Trip.status.in_(tm.COMPLETED_TRIP_STATUS)))
            .all()
        )
        return True if len(trips) != 0 else False

    def was_last_trip_a_parking_trip(self, sherpa_name: str):
        was_idling_trip = False
        last_trip = (
            self.dbsession.session.query(tm.Trip)
            .filter(tm.Trip.sherpa_name == sherpa_name)
            .filter(tm.Trip.status.in_(tm.COMPLETED_TRIP_STATUS))
            .filter(tm.Trip.start_time != None)
            .order_by(tm.Trip.start_time.desc())
            .first()
        )

        if last_trip is None:
            pass
        elif last_trip.booked_by == f"auto_park_{sherpa_name}":
            was_idling_trip = True

        return was_idling_trip

    def was_last_trip_a_battery_swap_trip(self, sherpa_name: str):
        was_battery_swap_trip = False
        last_trip = (
            self.dbsession.session.query(tm.Trip)
            .filter(tm.Trip.sherpa_name == sherpa_name)
            .filter(tm.Trip.status.in_(tm.COMPLETED_TRIP_STATUS))
            .filter(tm.Trip.start_time != None)
            .order_by(tm.Trip.start_time.desc())
            .first()
        )

        if last_trip is None:
            pass
        elif last_trip.booked_by == f"battery_swap_{sherpa_name}":
            was_battery_swap_trip = True

        return was_battery_swap_trip

    def get_num_booked_trips(self, trip_type):
        trips = (
            self.dbsession.session.query(tm.Trip)
            .filter(tm.Trip.booked_by.contains(trip_type))
            .filter(not_(tm.Trip.status.in_(tm.COMPLETED_TRIP_STATUS)))
            .all()
        )
        return len(trips)

    def book_auto_park_trips(self, config: dict, trip_type: str):
        idling_thresh = config["threshold"]
        trip_priority = config["priority"]

        idling_sherpa_status = self.get_idling_sherpa_status(idling_thresh)

        if len(idling_sherpa_status) == 0:
            logging.getLogger("misc").warning(f"No idling sherpas")

        for sherpa_status in idling_sherpa_status:
            park_at_any_station = False

            sherpa_name = sherpa_status.sherpa_name
            # fleet_name = sherpa_status.sherpa.fleet.name
            route_tag = f"parking_{sherpa_name}"
            saved_route = self.dbsession.get_saved_route(route_tag)

            if saved_route is None:
                route_tag = f"parking_{sherpa_status.sherpa.fleet.name}"
                saved_route = self.dbsession.get_saved_route(route_tag)
                park_at_any_station = True
                if saved_route is None:
                    logging.getLogger("misc").warning(f"No parking route for {sherpa_name}")
                    continue

            already_booked = self.is_trip_already_booked(sherpa_name, trip_type)

            if already_booked:
                logging.getLogger("misc").info(
                    f"conditional trip booked already for {sherpa_name}"
                )
                continue

            already_parked = False
            if park_at_any_station and sherpa_status.sherpa.parking_id:
                if sherpa_status.sherpa.parking_id in any(saved_route.route):
                    already_parked = True
            elif sherpa_status.sherpa.parking_id == saved_route.route[-1]:
                already_parked = True

            if already_parked:
                logging.getLogger("misc").info(
                    f"{sherpa_name} already parked at {sherpa_status.sherpa.parking_id}"
                )
                continue

            parking_route = None
            if park_at_any_station:
                for p_station_name in saved_route.route:
                    if not self.is_station_already_booked_with_conditional_trip(
                        trip_type, p_station_name
                    ):
                        parking_station_name = p_station_name
                        parking_route = [parking_station_name]
                        break
                    else:
                        logging.getLogger("misc").error(
                            f"{p_station_name} is already booked with {trip_type} trip"
                        )
            else:
                parking_station_name = saved_route.route[-1]
                parking_route = saved_route.route

            if parking_route is None:
                logging.getLogger("misc").info(
                    f"Couldn't find any parking spot for {sherpa_name}"
                )
                continue

            parking_station = self.dbsession.get_station_if_present(parking_station_name)
            if parking_station is None:
                logging.getLogger("misc").error(
                    f"Invalid station: {parking_station} in given route: {route_tag}"
                )
                continue

            if parking_station.parked_sherpa is not None:
                logging.getLogger("misc").info(
                    f"Cannot use {parking_station.name} for parking, {parking_station.parked_sherpa.name} is already parked there"
                )
                continue

            enqueue_trip_msg(
                sherpa_status.sherpa_name, parking_route, trip_type, trip_priority
            )
            logging.getLogger("misc").info(
                f"queued a {trip_type} trip for {sherpa_name} with route: {parking_route}, priority: {trip_priority}"
            )

    def book_battery_swap_trips(self, config: dict, trip_type: str):
        battery_level_thresh = config["threshold"]
        trip_priority = config["priority"]
        max_trips = config["max_trips"]

        low_battery_sherpa_status = self.get_low_battery_sherpa_status(battery_level_thresh)

        if len(low_battery_sherpa_status) == 0:
            logging.getLogger("misc").warning(f"No low battery sherpas")

        for sherpa_status in low_battery_sherpa_status:
            sherpa_name = sherpa_status.sherpa_name
            fleet_name = sherpa_status.sherpa.fleet.name

            logging.getLogger("misc").warning(
                f"Battery level of {sherpa_name} below {battery_level_thresh}, {sherpa_status.battery_status}"
            )

            saved_route = self.dbsession.get_saved_route(f"battery_swap_{fleet_name}")
            if saved_route is None:
                logging.getLogger("misc").warning(f"No battery_swap route for {fleet_name}")
                continue

            already_booked = self.is_trip_already_booked(sherpa_name, trip_type)

            if already_booked:
                logging.getLogger("misc").info(
                    f"conditional trip booked already for {sherpa_name}"
                )
                continue

            was_battery_swap_trip = self.was_last_trip_a_battery_swap_trip(sherpa_name)
            if was_battery_swap_trip:
                logging.getLogger("misc").info(
                    f"last trip was a conditional trip of type {trip_type}, need not book again"
                )
                continue

            num_trips = self.get_num_booked_trips(trip_type)

            if num_trips < max_trips:
                enqueue_trip_msg(
                    sherpa_status.sherpa_name, saved_route.route, trip_type, trip_priority
                )
                logging.getLogger("misc").info(
                    f"queued a {trip_type} trip for {sherpa_name} with route: {saved_route.route}, priority: {trip_priority}"
                )

            else:
                logging.getLogger("misc").info(
                    f"can only book {max_trips} trips, num {trip_type} trips: {num_trips}"
                )


def book_conditional_trips():
    logging.getLogger("misc").info("Started book conditional trips script")

    conditional_trip_config = get_conditional_trip_config()
    if conditional_trip_config is None:
        logging.getLogger("misc").error("Will not run conditional trips script config")
        return

    trip_types = conditional_trip_config.get("trip_types", [])

    while True:
        bct = BookConditionalTrip(None, trip_types, conditional_trip_config)
        for trip_type in bct.trip_types:
            with DBSession() as dbsession:
                bct.dbsession = dbsession
                bct.book_trip(trip_type)

        time.sleep(60)
