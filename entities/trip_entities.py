import time
from typing import List
from core.db import session_maker, engine

from entities.base_entities import JsonMixin
from entities.fleet_entities import add_or_update_sherpa
from models import fleet_models, trip_models
from models.fleet_models import SherpaModel
from models.trip_models import OngoingTripModel, TripLegModel, TripModel, TripStatus
from utils.util import ts_to_str


class Trip(JsonMixin):
    # id of this trip in the trips table.
    trip_id: str = None
    route: List = []
    status: str = None
    # sherpa assigned to this trip.
    sherpa: str = None
    # all the stations in the booking plus other automatically added stations such
    # as parking or hitching stations.
    augmented_route: List = []
    # index into the stations in augmented route.
    _next_station_idx: int = 0

    def __init__(self, route, priority=0, metadata=None):
        self.trip_id = self.record_trip_book(route, priority, metadata)
        self.augmented_route = self.route = route
        self.status = TripStatus.BOOKED

    def __repr__(self) -> str:
        return str(self.__dict__)

    def assign(self, sherpa: str):
        self.record_trip_assigned(sherpa)
        self.sherpa = sherpa
        self.status = TripStatus.ASSIGNED

    def add_station(self, station: str, index: int):
        self.augmented_route[index] = station

    def curr_station(self):
        if self._next_station_idx > 0:
            return self.augmented_route[self._next_station_idx - 1]
        else:
            return None

    def next_station(self):
        if self._next_station_idx < len(self.augmented_route):
            return self.augmented_route[self._next_station_idx]
        else:
            return None

    def start(self):
        self.record_trip_start()

    def end(self, success=True):
        self.record_trip_end(success)
        self.status = TripStatus.SUCCEEDED if success else TripStatus.FAILED

    def reached(self):
        self.record_trip_leg_end()
        self.status = TripStatus.WAITING_STATION
        self._next_station_idx += 1
        if self.finished():
            self.end(success=True)

    def finished(self):
        return self._next_station_idx >= len(self.augmented_route)

    def move(self):
        self.record_trip_leg_start()
        self.status = TripStatus.EN_ROUTE

    def record_trip_book(self, route, priority, metadata):
        with session_maker() as db:
            # create a new entry in the trips table.
            db_trip = TripModel(
                booking_time=ts_to_str(time.time()),
                route=route,
                status=TripStatus.BOOKED,
                priority=priority,
                trip_metadata=metadata,
            )
            db.add(db_trip)
            db.commit()
            db.refresh(db_trip)
            trip_id = db_trip.id

        return trip_id

    def record_trip_assigned(self, sherpa):
        with session_maker() as db:
            # create a new entry in the ongoing trips table.
            db_ongoing_trip = OngoingTripModel(trip_id=self.trip_id)
            db.add(db_ongoing_trip)
            db.flush()
            db.refresh(db_ongoing_trip)
            # get sherpa by name.
            db_sherpa: SherpaModel = (
                db.query(SherpaModel).filter(SherpaModel.name == sherpa).one()
            )
            # update status and sherpa id in trips table.
            db_ongoing_trip.trip.sherpa_id = db_sherpa.id
            db_ongoing_trip.trip.status = TripStatus.ASSIGNED

            db.commit()

    def record_trip_start(self):
        with session_maker() as db:
            # add start time to trips table.
            db_trip: TripModel = (
                db.query(TripModel).filter(TripModel.id == self.trip_id).one()
            )
            db_trip.start_time = ts_to_str(time.time())

            db.commit()

    def record_trip_end(self, success):
        with session_maker() as db:
            # add end time to trips table and update status.
            db_trip: TripModel = (
                db.query(TripModel).filter(TripModel.id == self.trip_id).one()
            )
            db_trip.end_time = ts_to_str(time.time())
            db_trip.status = TripStatus.SUCCEEDED if success else TripStatus.FAILED
            # remove entry from ongoing trips table.
            db.query(OngoingTripModel).filter(
                OngoingTripModel.trip_id == self.trip_id
            ).delete(synchronize_session=False)

            db.commit()

    def record_trip_leg_start(self):
        with session_maker() as db:
            # insert new trip leg record.
            trip_leg = TripLegModel(
                trip_id=self.trip_id,
                start_time=ts_to_str(time.time()),
                from_station=self.curr_station(),
                to_station=self.next_station(),
            )
            db.add(trip_leg)
            db.flush()
            db.refresh(trip_leg)
            # update ongoing trip table with trip leg id.
            db_ongoing_trip: OngoingTripModel = (
                db.query(OngoingTripModel)
                .filter(OngoingTripModel.trip_id == self.trip_id)
                .one()
            )
            db_ongoing_trip.trip_leg_id = trip_leg.id
            # update status of trip table.
            db_ongoing_trip.trip.status = TripStatus.EN_ROUTE

            db.commit()

    def record_trip_leg_end(self):
        with session_maker() as db:
            db_ongoing_trip: OngoingTripModel = (
                db.query(OngoingTripModel)
                .filter(OngoingTripModel.trip_id == self.trip_id)
                .one()
            )
            # update end time of trip leg.
            db_ongoing_trip.trip_leg.end_time = ts_to_str(time.time())
            # update status of trip table.
            db_ongoing_trip.trip.status = TripStatus.WAITING_STATION

            db.commit()


def test():
    fleet_models.Base.metadata.drop_all(bind=engine)
    trip_models.Base.metadata.drop_all(bind=engine)
    fleet_models.Base.metadata.create_all(bind=engine)
    trip_models.Base.metadata.create_all(bind=engine)

    add_or_update_sherpa("S1")

    trip = Trip(["a", "b", "c"], 0)
    trip.assign("S1")
    trip.start()
    time.sleep(2)
    trip.move()
    time.sleep(5)
    trip.reached()
    time.sleep(2)
    trip.move()
    time.sleep(5)
    trip.reached()
    time.sleep(2)
    trip.move()
    time.sleep(5)
    trip.reached()
    print(trip)
    # with session_maker() as db:
    # db_trip: TripModel = db.query(TripModel).filter(TripModel.id == trip.trip_id).one()
    # fleet_models.Base.metadata.drop_all(bind=engine)
    # trip_models.Base.metadata.drop_all(bind=engine)


if __name__ == "__main__":
    test()
