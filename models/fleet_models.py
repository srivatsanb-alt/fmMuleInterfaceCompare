from sqlalchemy import (
    ARRAY,
    Boolean,
    Column,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    DateTime,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from models.base_models import Base, StationProperties, TimestampMixin
from models.visa_models import VisaAssignment


class Map(TimestampMixin, Base):
    __tablename__ = "maps"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    files = relationship("MapFile", back_populates="map")


class MapFile(TimestampMixin, Base):
    __tablename__ = "map_files"

    id = Column(Integer, primary_key=True, index=True)
    map_id = Column(Integer, ForeignKey("maps.id"))
    map = relationship("Map", back_populates="files")

    filename = Column(String, index=True)
    file_hash = Column(String)


class Fleet(Base):
    __tablename__ = "fleets"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    customer = Column(String)
    site = Column(String)
    location = Column(String)
    status = Column(String, index=True)

    map_id = Column(Integer, ForeignKey("maps.id"))
    map = relationship("Map")
    sherpas = relationship("Sherpa", back_populates="fleet")
    stations = relationship("Station", back_populates="fleet")


class Sherpa(Base):
    __tablename__ = "sherpas"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    hwid = Column(String, unique=True)
    ip_address = Column(String)
    port = Column(String)
    hashed_api_key = Column(String, unique=True, index=True)

    fleet_id = Column(Integer, ForeignKey("fleets.id"), nullable=False)
    fleet = relationship("Fleet", back_populates="sherpas")

    status = relationship("SherpaStatus", back_populates="sherpa", uselist=False)
    exclusion_zones = relationship(
        "ExclusionZone", secondary=VisaAssignment.__table__, back_populates="sherpas"
    )


class SherpaEvent(TimestampMixin, Base):
    __tablename__ = "sherpa_events"

    id = Column(Integer, primary_key=True, index=True)
    sherpa_name = Column(String, index=True)
    msg_type = Column(String, index=True)
    context = Column(String, index=True)


class SherpaStatus(TimestampMixin, Base):
    __tablename__ = "sherpastatus"

    sherpa_name = Column(String, ForeignKey("sherpas.name"), primary_key=True, index=True)
    sherpa = relationship("Sherpa", back_populates="status")

    initialized = Column(Boolean)
    disabled = Column(Boolean, index=True)
    inducted = Column(Boolean, index=True)
    idle = Column(Boolean)
    error = Column(String)
    pose = Column(ARRAY(Float))
    battery_status = Column(Float)
    mode = Column(String, index=True)
    trip_id = Column(Integer)
    trip_leg_id = Column(Integer)
    assign_next_task = Column(Boolean, index=True)
    continue_curr_task = Column(Boolean)
    disabled_reason = Column(String)
    other_info = Column(JSONB)


class Station(Base):
    __tablename__ = "stations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    pose = Column(ARRAY(Float))
    properties = Column(ARRAY(Enum(StationProperties)))
    button_id = Column(String)
    fleet_id = Column(Integer, ForeignKey("fleets.id"), nullable=False)
    fleet = relationship("Fleet", back_populates="stations")
    status = relationship("StationStatus", back_populates="station", uselist=False)


class StationStatus(TimestampMixin, Base):
    __tablename__ = "stationstatus"

    station_name = Column(String, ForeignKey("stations.name"), primary_key=True, index=True)
    station = relationship("Station", back_populates="status")
    disabled = Column(Boolean)
    arriving_sherpas = Column(ARRAY(String))
    sherpa_at_station = Column(String)


class AvailableSherpas(TimestampMixin, Base):
    __tablename__ = "available_sherpas"
    sherpa_name = Column(String, primary_key=True, index=True)
    fleet_name = Column(String, index=True)
    available = Column(Boolean, index=True)


class OptimalDispatchState(Base):
    __tablename__ = "optimal_dispatch_state"
    fleet_name = Column(String, primary_key=True, index=True)
    last_assignment_time = Column(DateTime, index=True)
