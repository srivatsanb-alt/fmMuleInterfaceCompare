import datetime
from sqlalchemy import ARRAY, Column, DateTime, ForeignKey, Integer, String, Boolean, Float
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
    EN_ROUTE = "en_route"
    WAITING_STATION = "waiting_station"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TripLegStatus:
    STARTED = "started moving"
    ENDED = "finished moving"
    MOVING = "moving"
    MOVING_SLOW = "moving slow"
    STOPPED = "stopped"


COMPLETED_TRIP_STATUS = [TripStatus.SUCCEEDED, TripStatus.FAILED, TripStatus.CANCELLED]
ONGOING_TRIP_STATUS = [TripStatus.WAITING_STATION, TripStatus.EN_ROUTE]
YET_TO_START_TRIP_STATUS = [TripStatus.BOOKED, TripStatus.ASSIGNED]
ACTIVE_TRIP_STATUS = [
    TripStatus.WAITING_STATION,
    TripStatus.EN_ROUTE,
    TripStatus.BOOKED,
    TripStatus.ASSIGNED,
]


class TripState:
    WAITING_STATION_AUTO_HITCH_START = "waiting_station_auto_hitch_start"
    WAITING_STATION_AUTO_HITCH_END = "waiting_station_auto_hitch_end"
    WAITING_STATION_AUTO_UNHITCH_START = "waiting_station_auto_unhitch_start"
    WAITING_STATION_AUTO_UNHITCH_END = "waiting_station_auto_unhitch_end"
    WAITING_STATION_DISPATCH_START = "waiting_station_dispatch_start"
    WAITING_STATION_DISPATCH_END = "waiting_station_dispatch_end"
    WAITING_STATION_CONV_RECEIVE_START = "waiting_station_conv_receive_start"
    WAITING_STATION_CONV_RECEIVE_END = "waiting_station_conv_receive_end"
    WAITING_STATION_CONV_SEND_START = "waiting_station_conv_send_start"
    WAITING_STATION_CONV_SEND_END = "waiting_station_conv_send_end"


class TripAnalytics(Base, TimestampMixin):
    __tablename__ = "trip_analytics"
    sherpa_name = Column(String, index=True)
    trip_id = Column(Integer, index=True)
    trip_leg_id = Column(Integer, primary_key=True, index=True)
    start_time = Column(DateTime, index=True)
    end_time = Column(DateTime, index=True)
    from_station = Column(String, index=True)
    to_station = Column(String, index=True)
    cte = Column(Float)
    te = Column(Float)
    route_length = Column(Float)
    progress = Column(Float)
    expected_trip_time = Column(Float)
    actual_trip_time = Column(Float)
    time_elapsed_obstacle_stoppages = Column(Float)
    time_elapsed_visa_stoppages = Column(Float)
    time_elapsed_other_stoppages = Column(Float)
    num_trip_msg = Column(Integer)


class SavedRoutes(Base):
    __tablename__ = "saved_routes"
    tag = Column(String, primary_key=True, index=True)
    route = Column(ARRAY(String))
    fleet_name = Column(String)
    other_info = Column(JSONB)


class Trip(Base, TimestampMixin):
    __tablename__ = "trips"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, index=True)

    # sherpa doing the trip
    sherpa_name = Column(String, index=True)

    # relate fleet table
    fleet_name = Column(String, index=True)

    # when trip was booked
    booking_time = Column(DateTime)
    # when trip started
    start_time = Column(DateTime, index=True)
    # when trip ended (sherpa could go to a parking station after this)
    end_time = Column(DateTime, index=True)

    # station names on route
    route = Column(ARRAY(String))
    # all the stations in the booking plus other automatically added stations such
    # as parking or hitching stations
    augmented_route = Column(ARRAY(String))
    # augmented route indices that are part of the booking route.
    aug_idxs_booked = Column(ARRAY(Integer))

    # BOOKED, ASSIGNED, WAITING_STATION, EN_ROUTE, SUCCEEDED, FAILED
    status = Column(String, index=True)
    route_lengths = Column(ARRAY(Float))
    etas_at_start = Column(ARRAY(Float))
    etas = Column(ARRAY(Float))

    scheduled = Column(Boolean, index=True)
    time_period = Column(Integer)

    # these come from the booking request
    priority = Column(Float)
    trip_metadata = Column(JSONB)

    booked_by = Column(String)

    # other details we may want to store about the trip
    other_info = Column(JSONB)

    def __init__(
        self,
        route,
        priority,
        metadata=None,
        fleet_name=None,
        booking_id=None,
        booked_by=None,
    ):

        self.fleet_name = fleet_name
        self.booking_id = booking_id
        self.booking_time = datetime.datetime.now()
        self.route = route
        self.status = TripStatus.BOOKED
        self.priority = priority
        self.scheduled = False
        self.time_period = 0
        self.trip_metadata = metadata
        self.booked_by = booked_by

        # set all milkrun trip details
        if metadata:
            scheduled = metadata.get("scheduled", "False")
            if eval(scheduled):
                self.scheduled = True
                start_time = str_to_dt(metadata["scheduled_start_time"])
                end_time = str_to_dt(metadata["scheduled_end_time"])
                if end_time < start_time:
                    raise ValueError("trip end time less than start time")

                self.time_period = int(metadata["scheduled_time_period"])

                if self.time_period <= 0:
                    raise ValueError("trip time period should be greater than zero")

                num_days_to_repeat = int(metadata.get("num_days_to_repeat", "0"))
                repeat_count = int(metadata.get("repeat_count", "0"))
                if num_days_to_repeat > 0 and repeat_count == 0:
                    if start_time.date() != end_time.date():
                        raise ValueError("Cannot repeat trip spanning over multiple days")
                    self.trip_metadata["actual_start_time"] = metadata[
                        "scheduled_start_time"
                    ]
                    self.trip_metadata["actual_end_time"] = metadata["scheduled_end_time"]
                    self.trip_metadata["repeat_count"] = "1"
                    flag_modified(self, "trip_metadata")

        self.augmented_route = route
        self.aug_idxs_booked = list(range(len(self.route)))

    def assign_sherpa(self, sherpa_name: str):
        self.sherpa_name = sherpa_name
        self.status = TripStatus.ASSIGNED

    def start(self):
        self.start_time = datetime.datetime.now()

    def end(self, success):
        self.etas = [0] * len(self.augmented_route)
        self.end_time = datetime.datetime.now()
        self.status = TripStatus.SUCCEEDED if success else TripStatus.FAILED

    def cancel(self):
        self.end_time = datetime.datetime.now()
        self.status = TripStatus.CANCELLED

    def update_etas(self, eta, idx):
        self.etas[idx] = eta
        flag_modified(self, "etas")

    def __repr__(self):
        return str(self.__dict__)


class PendingTrip(Base, TimestampMixin):
    __tablename__ = "pending_trips"
    trip_id = Column(Integer, ForeignKey("trips.id"), primary_key=True)
    sherpa_name = Column(String, index=True)
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

    # commenting out - NEEDS dashboard changes
    status = Column(String, index=True)
    stoppage_reason = Column(String)

    def __init__(self, trip_id, from_station, to_station):
        self.trip_id = trip_id
        self.start_time = datetime.datetime.now()
        self.to_station = to_station
        self.from_station = from_station
        self.status = TripLegStatus.STARTED

    def end(self):
        self.end_time = datetime.datetime.now()
        self.status = TripLegStatus.ENDED
        self.stoppage_reason = None

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

    def first_station(self):
        return self.trip.augmented_route[0]

    def curr_station(self):
        if self.next_idx_aug > 0:
            return self.trip.augmented_route[self.next_idx_aug - 1]

        elif self.next_idx_aug == 0 and self.trip.etas_at_start[0] == 0:
            return self.trip.augmented_route[0]

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

    def get_basic_trip_description(self):
        trip_metadata = self.trip.trip_metadata

        if trip_metadata is not None:
            desc = trip_metadata.get("description")

        waiting_reason = " "
        if len(self.states) != 0:
            waiting_reason = get_waiting_reason(self.states)

        temp = {
            "booked_by": self.trip.booked_by,
            "description": desc,
            "route": self.trip.augmented_route,
            "curr_station": self.curr_station(),
            "next_station": self.next_station(),
            "waiting_for": waiting_reason,
            "status": self.trip.status,
            "trip_id": self.trip.id,
            "trip_leg_id": self.trip_leg_id,
        }
        return temp


def is_start_state(state):
    return state.endswith(START)


def get_end_state(state):
    if not is_start_state(state):
        return state
    return state[: -len(START)] + END


def get_waiting_reason(states):
    temp = " "
    for state in states:
        if state.rsplit("_", 1)[-1] == START:
            if get_end_state(state) not in states:
                if temp == " ":
                    temp = "Waiting for"
                for x in state.split("_")[2:-1]:
                    temp += f" {x},"

    return temp[:-1]
