from sqlalchemy import ARRAY, Column, DateTime, ForeignKey, Integer, String
from models.base_models import Base, TimestampMixin
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB


class TripStatus:
    BOOKED = "booked"
    ASSIGNED = "assigned"
    WAITING_STATION = "waiting_station"
    EN_ROUTE = "en_route"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class TripModel(Base, TimestampMixin):
    __tablename__ = "trips"

    id = Column(Integer, primary_key=True, index=True)

    # sherpa doing the trip
    sherpa_id = Column(Integer, ForeignKey("sherpas.id"))
    sherpa = relationship("SherpaModel")

    # when trip was booked
    booking_time = Column(DateTime)
    # when trip started
    start_time = Column(DateTime)
    # when trip ended (sherpa could go to a parking station after this)
    end_time = Column(DateTime)

    # station names on route
    route = Column(ARRAY(String))
    # BOOKED, ASSIGNED, WAITING_STATION, EN_ROUTE, SUCCEEDED, FAILED
    status = Column(String)

    # these come from the booking request
    priority = Column(Integer)
    trip_metadata = Column(JSONB)

    # other details we may want to store about the trip
    other_info = Column(JSONB)


class PendingTripModel(Base, TimestampMixin):
    __tablename__ = "pending_trips"
    trip_id = Column(Integer, ForeignKey("trips.id"), primary_key=True)
    trip = relationship("TripModel")


class TripLegModel(Base, TimestampMixin):
    __tablename__ = "trip_legs"

    id = Column(Integer, primary_key=True, index=True)
    # trip this leg belongs to
    trip_id = Column(Integer, ForeignKey("trips.id"))
    trip = relationship("TripModel")

    # when this leg started
    start_time = Column(DateTime)
    # when this leg ended
    end_time = Column(DateTime)

    # start and end points of leg
    from_station = Column(String)
    to_station = Column(String)


class OngoingTripModel(Base, TimestampMixin):
    __tablename__ = "ongoing_trips"
    trip_id = Column(Integer, ForeignKey("trips.id"), primary_key=True)
    trip = relationship("TripModel")
    trip_leg_id = Column(Integer, ForeignKey("trip_legs.id"))
    trip_leg = relationship("TripLegModel")
