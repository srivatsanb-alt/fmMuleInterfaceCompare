# python module imports
import datetime
import time
import os
import toml
from sqlalchemy.sql import not_

# ati code imports
from models.db_session import DBSession
import models.trip_models as tm
import models.fleet_models as fm
import models.request_models as rqm
import app.routers.dependencies as dpd
from core.logs import get_logger


def get_conditional_trip_config():
    conf_path = os.path.join(os.getenv("FM_CONFIG_DIR"), "conditional_trips.toml")

    if not os.path.exists(conf_path):
        get_logger("misc").error(f"conditional trip config : {conf_path} not found")
        return

    config = toml.load(conf_path)

    return config.get("conditional_trips", {})


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

    def book_trips(self):
        for trip_type in self.trip_types:
            book_fn = getattr(self, f"book_{trip_type}_trips", None)

            if book_fn is None:
                get_logger("misc").info(f"Invalid conditional trip type {trip_type}")
                continue

            config = self.config.get(trip_type)
            if config["book"]:
                book_fn(config, trip_type)

    def get_low_battery_sherpa_status(self, threshold: int):
        return (
            self.dbsession.session.query(fm.SherpaStatus)
            .filter(fm.SherpaStatus.battery_status < threshold)
            .filter(fm.SherpaStatus.battery_status != -1)
            .filter(fm.SherpaStatus.disabled is not True)
            .order_by(fm.SherpaStatus.battery_status)
            .all()
        )

    def get_idling_sherpa_status(self, threshold: int):
        temp = (
            self.dbsession.session.query(fm.SherpaStatus)
            .filter(fm.SherpaStatus.trip_id == None)
            .filter(fm.SherpaStatus.disabled is not True)
            .all()
        )

        idling_sherpa_status = []

        for sherpa_status in temp:
            today_now = datetime.datetime.now()
            sherpa_name = sherpa_status.sherpa_name
            last_trip = self.dbsession.last_trip(sherpa_name)

            if last_trip is None:
                continue

            if (today_now - last_trip.end_time).seconds > threshold:
                get_logger("misc").warning(f"{sherpa_name} has been found idling")
                idling_sherpa_status.append(sherpa_status)

        return idling_sherpa_status

    def is_trip_already_booked(self, sherpa_name: str, trip_type: str):
        trips = (
            self.dbsession.session.query(tm.Trip)
            .filter(tm.Trip.booked_by == f"{trip_type}_{sherpa_name}")
            .filter(not_(tm.Trip.status.in_(tm.COMPLETED_TRIP_STATUS)))
            .all()
        )
        return True if len(trips) != 0 else False

    def get_num_booked_trips(self, trip_type):
        trips = (
            self.dbsession.session.query(tm.Trip)
            .filter(tm.Trip.booked_by.contains(trip_type))
            .filter(not_(tm.Trip.status.in_(tm.COMPLETED_TRIP_STATUS)))
            .all()
        )
        return len(trips)

    def book_idling_sherpa_trips(self, config: dict, trip_type: str):
        idling_thresh = config["threshold"]
        trip_priority = config["priority"]
        max_trips = config["max_trips"]

        idling_sherpa_status = self.get_idling_sherpa_status(idling_thresh)

        for sherpa_status in idling_sherpa_status:
            sherpa_name = sherpa_status.sherpa_name
            fleet_name = sherpa_status.sherpa.fleet.name

            saved_route = self.dbsession.get_saved_route(f"idling_{fleet_name}")

            if saved_route is None:
                get_logger("misc").warning(f"No idling route for {fleet_name}")
                continue

            already_booked = self.is_trip_already_booked(sherpa_name, trip_type)

            if already_booked:
                get_logger("misc").info(f"Idling trip booked already for {sherpa_name}")
                continue

            num_trips = self.get_num_booked_trips(trip_type)

            if num_trips < max_trips:
                enqueue_trip_msg(
                    sherpa_status.sherpa_name, saved_route.route, trip_type, trip_priority
                )
                get_logger("misc").info(
                    f"queued a {trip_type} trip for {sherpa_name} with route: {saved_route.route}, priority: {trip_priority}"
                )

            else:
                get_logger("misc").info(
                    f"can only book {max_trips} trips, num {trip_type} trips: {num_trips}"
                )

    def book_battery_swap_trips(self, config: dict, trip_type: str):
        battery_level_thresh = config["threshold"]
        trip_priority = config["priority"]
        max_trips = config["max_trips"]

        low_battery_sherpa_status = self.get_low_battery_sherpa_status(battery_level_thresh)

        for sherpa_status in low_battery_sherpa_status:
            sherpa_name = sherpa_status.sherpa_name
            fleet_name = sherpa_status.sherpa.fleet.name

            get_logger("misc").warning(
                f"Battery level of {sherpa_name} below {battery_level_thresh}, {sherpa_status.battery_status}"
            )

            saved_route = self.dbsession.get_saved_route(f"battery_swap_{fleet_name}")
            if saved_route is None:
                get_logger("misc").warning(f"No battery_swap route for {fleet_name}")
                continue

            already_booked = self.is_trip_already_booked(sherpa_name, trip_type)

            if already_booked:
                get_logger("misc").info(
                    f"Battery swap trip booked already for {sherpa_name}"
                )
                continue

            num_trips = self.get_num_booked_trips(trip_type)

            if num_trips < max_trips:
                enqueue_trip_msg(
                    sherpa_status.sherpa_name, saved_route.route, trip_type, trip_priority
                )
                get_logger("misc").info(
                    f"queued a {trip_type} trip for {sherpa_name} with route: {saved_route.route}, priority: {trip_priority}"
                )

            else:
                get_logger("misc").info(
                    f"can only book {max_trips} trips, num {trip_type} trips: {num_trips}"
                )


def book_conditional_trips():
    get_logger("misc").info("Started book conditional trips script")

    conditional_trip_config = get_conditional_trip_config()
    if conditional_trip_config is None:
        get_logger("misc").error("Will not run conditional trips script config")
        return

    trip_types = conditional_trip_config.get("trip_types", [])

    while True:
        with DBSession() as dbsession:
            bct = BookConditionalTrip(dbsession, trip_types, conditional_trip_config)
            bct.book_trips()

        time.sleep(60)
