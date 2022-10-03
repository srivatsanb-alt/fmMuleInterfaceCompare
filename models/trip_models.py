import datetime
from sqlalchemy import ARRAY, Column, DateTime, ForeignKey, Integer, String, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.orm.attributes import flag_modified
from utils.util import str_to_dt

from models.base_models import Base, TimestampMixin

START = "start"
END = "end"


class TripStatus:
    BOOKED = "booked"
    ASSIGNED = "assigned"
    WAITING_STATION = "waiting_station"
    EN_ROUTE = "en_route"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TripState:
    WAITING_STATION_AUTO_HITCH_START = "waiting_station_auto_hitch_start"
    WAITING_STATION_AUTO_HITCH_END = "waiting_station_auto_hitch_end"
    WAITING_STATION_AUTO_UNHITCH_START = "waiting_station_auto_unhitch_start"
    WAITING_STATION_AUTO_UNHITCH_END = "waiting_station_auto_unhitch_end"
    WAITING_STATION_DISPATCH_START = "waiting_station_dispatch_start"
    WAITING_STATION_DISPATCH_END = "waiting_station_dispatch_end"


class Trip(Base, TimestampMixin):
    __tablename__ = "trips"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer)

    # sherpa doing the trip
    sherpa_name = Column(String, ForeignKey("sherpas.name"))
    sherpa = relationship("Sherpa")

    # relate fleet table
    fleet_name = Column(String, ForeignKey("fleets.name"))
    fleet = relationship("Fleet")

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

    milkrun = Column(Boolean)
    time_period = Column(Integer)

    # these come from the booking request
    priority = Column(Integer)
    trip_metadata = Column(JSONB)

    # other details we may want to store about the trip
    other_info = Column(JSONB)

    def __init__(self, route, priority=0, metadata=None, fleet_name=None, booking_id=None):
        self.fleet_name = fleet_name
        self.booking_id = booking_id
        self.booking_time = datetime.datetime.now()
        self.route = route
        self.status = TripStatus.BOOKED
        self.priority = priority
        self.milkrun = False
        self.time_period = 0
        self.trip_metadata = metadata

        # set all milkrun trip details
        if metadata.get("milkrun"):
            self.milkrun = True
            self.start_time = str_to_dt(metadata["milkrun_start_time"])
            self.end_time = str_to_dt(metadata["milkrun_end_time"])
            self.time_period = int(metadata["milkrun_time_period"])

        self.augmented_route = route
        self.aug_idxs_booked = list(range(len(self.augmented_route)))

    def assign_sherpa(self, sherpa: str):
        self.sherpa_name = sherpa
        self.status = TripStatus.ASSIGNED

    def start(self):
        self.start_time = datetime.datetime.now()

    def end(self, success):
        self.end_time = datetime.datetime.now()
        self.status = TripStatus.SUCCEEDED if success else TripStatus.FAILED

    def __repr__(self):
        return str(self.__dict__)


class PendingTrip(Base, TimestampMixin):
    __tablename__ = "pending_trips"
    trip_id = Column(Integer, ForeignKey("trips.id"), primary_key=True)
    sherpa_name = Column(String)
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
        self.start_time = datetime.datetime.now()
        self.from_station = datetime.datetime.now()
        self.to_station = to_station

    def end(self):
        self.end_time = datetime.datetime.now()

    def finished(self):
        return True if self.end_time else False


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
    # list of TripStates
    states = Column(ARRAY(String), server_default="{}")

    def init(self):
        self.next_idx_aug = 0
        self.next_idx = 0 if 0 in self.trip.aug_idxs_booked else -1
        self.states = []

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
        self.states.clear()

    def end_leg(self):
        self.trip.status = TripStatus.WAITING_STATION
        if self.next_idx_aug in self.trip.aug_idxs_booked:
            self.next_idx += 1
        self.next_idx_aug += 1
        if self.finished():
            self.trip.end(success=True)

    def finished(self):
        if not self.check_continue():
            return False
        return self.next_idx_aug >= len(self.trip.augmented_route)

    def finished_booked(self):
        return self.next_idx >= len(self.trip.route)

    def check_continue(self):
        # Trip can continue if every state has a matching end state.
        return all([get_end_state(state) in self.states for state in self.states])

    def add_state(self, state):
        self.states.append(state)
        flag_modified(self, "states")

    def clear_states(self):
        self.states.clear()
        flag_modified(self, "states")


def is_start_state(state):
    return state.endswith(START)


def get_end_state(state):
    if not is_start_state(state):
        return state
    return state[: -len(START)] + END
