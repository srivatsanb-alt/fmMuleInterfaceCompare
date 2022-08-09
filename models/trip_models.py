import time
from sqlalchemy import ARRAY, Column, DateTime, ForeignKey, Integer, String
from models.base_models import Base, TimestampMixin
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB

from utils.util import ts_to_str


class TripStatus:
    BOOKED = "booked"
    ASSIGNED = "assigned"
    WAITING_STATION = "waiting_station"
    EN_ROUTE = "en_route"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class Trip(Base, TimestampMixin):
    __tablename__ = "trips"

    id = Column(Integer, primary_key=True, index=True)

    # sherpa doing the trip
    sherpa_name = Column(String, ForeignKey("sherpas.name"))
    sherpa = relationship("Sherpa")

    # when trip was booked
    booking_time = Column(DateTime)
    # when trip started
    start_time = Column(DateTime)
    # when trip ended (sherpa could go to a parking station after this)
    end_time = Column(DateTime)

    # station names on route
    route = Column(ARRAY(String))
    # all the stations in the booking plus other automatically added stations such
    # as parking or hitching stations
    augmented_route = Column(ARRAY(String))
    # augmented route indices that are part of the booking route.
    aug_idxs_booked = Column(ARRAY(Integer))

    # BOOKED, ASSIGNED, WAITING_STATION, EN_ROUTE, SUCCEEDED, FAILED
    status = Column(String)

    # these come from the booking request
    priority = Column(Integer)
    trip_metadata = Column(JSONB)

    # other details we may want to store about the trip
    other_info = Column(JSONB)

    def __init__(self, route, priority=0, metadata=None):
        self.booking_time = ts_to_str(time.time())
        self.route = route
        self.status = TripStatus.BOOKED
        self.priority = priority
        self.trip_metadata = metadata
        self.augmented_route = route
        self.aug_idxs_booked = list(range(len(self.augmented_route)))

    def assign_sherpa(self, sherpa: str):
        self.sherpa_name = sherpa
        self.status = TripStatus.ASSIGNED

    def start(self):
        self.start_time = ts_to_str(time.time())

    def end(self, success):
        self.end_time = ts_to_str(time.time())
        self.status = TripStatus.SUCCEEDED if success else TripStatus.FAILED

    def __repr__(self):
        return str(self.__dict__)


class PendingTrip(Base, TimestampMixin):
    __tablename__ = "pending_trips"
    trip_id = Column(Integer, ForeignKey("trips.id"), primary_key=True)
    trip = relationship("Trip")


class TripLeg(Base, TimestampMixin):
    __tablename__ = "trip_legs"

    id = Column(Integer, primary_key=True, index=True)
    # trip this leg belongs to
    trip_id = Column(Integer, ForeignKey("trips.id"), index=True)
    trip = relationship("Trip")

    # when this leg started
    start_time = Column(DateTime)
    # when this leg ended
    end_time = Column(DateTime)

    # start and end points of leg
    from_station = Column(String)
    to_station = Column(String)

    def __init__(self, trip_id, from_station, to_station):
        self.trip_id = trip_id
        self.start_time = ts_to_str(time.time())
        self.from_station = from_station
        self.to_station = to_station

    def end(self):
        self.end_time = ts_to_str(time.time())


class OngoingTrip(Base, TimestampMixin):
    __tablename__ = "ongoing_trips"
    sherpa_name = Column(String, index=True)
    trip_id = Column(Integer, ForeignKey("trips.id"), primary_key=True, index=True)
    trip = relationship("Trip")
    trip_leg_id = Column(Integer, ForeignKey("trip_legs.id"))
    trip_leg = relationship("TripLeg")

    # index into the stations in booking route.
    next_idx = Column(Integer)
    # index into the stations in augmented route.
    next_idx_aug = Column(Integer)

    def init(self):
        self.next_idx_aug = 0
        self.next_idx = 0 if 0 in self.trip.aug_idxs_booked else -1

    def curr_station(self):
        if self.next_idx_aug > 0:
            return self.trip.augmented_route[self.next_idx_aug - 1]
        else:
            return None

    def next_station(self):
        if self.next_idx_aug < len(self.trip.augmented_route):
            return self.trip.augmented_route[self.next_idx_aug]
        else:
            return None

    def start_leg(self, trip_leg_id):
        self.trip_leg_id = trip_leg_id
        self.trip.status = TripStatus.EN_ROUTE

    def end_leg(self):
        self.trip.status = TripStatus.WAITING_STATION
        self.next_idx_aug += 1
        if self.next_idx_aug in self.trip.aug_idxs_booked:
            self.next_idx += 1
        if self.finished():
            self.trip.end(success=True)

    def finished(self):
        return self.next_idx_aug >= len(self.trip.augmented_route)

    def finished_booked(self):
        return self.next_idx >= len(self.trip.route)

    def set_leg_id(self, trip_leg_id):
        self.trip_leg_id = trip_leg_id
