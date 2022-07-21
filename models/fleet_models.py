from sqlalchemy import ARRAY, Boolean, Column, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from models.base_models import Base, TimestampMixin


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


class FleetModel(TimestampMixin, Base):
    __tablename__ = "fleets"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    customer = Column(String)
    site = Column(String)
    location = Column(String)

    map_id = Column(Integer, ForeignKey("maps.id"))
    map = relationship("Map")
    sherpas = relationship("SherpaModel", back_populates="fleet")


class SherpaModel(TimestampMixin, Base):
    __tablename__ = "sherpas"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    hwid = Column(String, unique=True)
    ip_address = Column(String, unique=True)
    hashed_api_key = Column(String, unique=True, index=True)

    initialized = Column(Boolean)
    disabled = Column(Boolean)
    error = Column(String)

    pose = Column(ARRAY(Float))
    trip_id = Column(Integer)
    trip_leg_id = Column(Integer)

    fleet_id = Column(Integer, ForeignKey("fleets.id"))
    fleet = relationship("FleetModel", back_populates="sherpas")

    other_info = Column(JSONB)
