from sqlalchemy import ARRAY, Boolean, Column, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from models.base_models import Base, StationProperties, TimestampMixin


class Map(TimestampMixin, Base):
    __tablename__ = "maps"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    files = relationship("MapFile", back_populates="map")


class MapFile(TimestampMixin, Base):
    __tablename__ = "map_files"

    id = Column(Integer, primary_key=True, index=True)
    map_id = Column(Integer, ForeignKey("maps.id"))
    map = relationship("Map", back_populates="files")

    filename = Column(String)
    file_hash = Column(String)


class Fleet(Base):
    __tablename__ = "fleets"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    customer = Column(String)
    site = Column(String)
    location = Column(String)
    status = Column(String)

    map_id = Column(Integer, ForeignKey("maps.id"))
    map = relationship("Map")
    sherpas = relationship("Sherpa", back_populates="fleet")
    stations = relationship("Station", back_populates="fleet")


class Sherpa(Base):
    __tablename__ = "sherpas"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    hwid = Column(String, unique=True)
    ip_address = Column(String, unique=True)
    hashed_api_key = Column(String, unique=True, index=True)

    fleet_id = Column(Integer, ForeignKey("fleets.id"))
    fleet = relationship("Fleet", back_populates="sherpas")

    status = relationship("SherpaStatus", back_populates="sherpa", uselist=False)
    exclusion_zones = relationship(
        "ExclusionZone", secondary="visa_assignments", back_populates="sherpas"
    )


class SherpaStatus(TimestampMixin, Base):
    __tablename__ = "sherpastatus"

    sherpa_name = Column(String, ForeignKey("sherpas.name"), primary_key=True, index=True)
    sherpa = relationship("Sherpa", back_populates="status")

    initialized = Column(Boolean)
    disabled = Column(Boolean)
    idle = Column(Boolean)
    error = Column(String)

    pose = Column(ARRAY(Float))
    battery_status = Column(Float)
    mode = Column(String)

    trip_id = Column(Integer)
    trip_leg_id = Column(Integer)

    other_info = Column(JSONB)


class Station(Base):
    __tablename__ = "stations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    pose = Column(ARRAY(Float))
    properties = Column(ARRAY(Enum(StationProperties)))
    button_id = Column(String)
    fleet_id = Column(Integer, ForeignKey("fleets.id"), nullable = False)
    fleet = relationship("Fleet", back_populates="stations")


class StationStatus(TimestampMixin, Base):
    __tablename__ = "stationstatus"

    station_name = Column(String, ForeignKey("stations.name"), primary_key=True, index=True)
    station = relationship("Station")

    disabled = Column(Boolean)
    arriving_sherpas = Column(ARRAY(String))
    sherpa_at_station = Column(String)
