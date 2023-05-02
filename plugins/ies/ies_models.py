import logging
import os
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
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine
from sqlalchemy import Integer, String, Column, ARRAY
from pydantic import BaseModel
from plugin_db import Base
import plugins.ies.ies_utils as iu


class DBSession:
    def __init__(self):
        engine = create_engine(os.path.join(os.getenv("FM_DATABASE_URI"), "plugin_ies"))
        session_maker = sessionmaker(autocommit=False, autoflush=True, bind=engine)
        self.session: Session = session_maker()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type or exc_value or traceback:
            self.close(commit=False)
        else:
            self.close()

    def close(self, commit=True):
        if commit:
            self.session.commit()
        self.session.close()

    def get_ati_station_name(self, ies_station_name):
        station = (
            self.session.query(IESStations)
            .filter(IESStations.ies_name == ies_station_name)
            .one_or_none()
        )
        if station is None:
            return None
        return station.ati_name

    def get_consolidation_info(self, fleet_name: str, start_station: str, route_tag: str):
        all_ies_routes = iu.get_all_ies_routes(fleet_name)
        if all_ies_routes != {}:
            logging.getLogger("plugin_ies").info(
                f"filtering bookings, route: {all_ies_routes[route_tag]}"
            )
            filtered_bookings = (
                self.session.query(IESBookingReq)
                .filter(IESBookingReq.start_station == start_station)
                .filter(IESBookingReq.route[2].in_(all_ies_routes[route_tag]))
                .all()
            )
        else:
            raise ValueError(f"No IES routes defined")
        return filtered_bookings


class IESBookingReq(Base):
    __tablename__ = "ies_booking_req"
    __table_args__ = {"extend_existing": True}
    ext_ref_id = Column(String, primary_key=True, index=True)
    start_station = Column(String)
    route = Column(ARRAY(String))
    status = Column(String)
    kanban_id = Column(String, index=True)
    deadline = Column(String)
    combined_trip_id = Column(ForeignKey("combined_trips.trip_id"))
    combined_trip = relationship(
        "CombinedTrips",
        back_populates="trips",
        uselist=False,
    )
    other_info = Column(JSONB)


class CombinedTrips(Base):
    __tablename__ = "combined_trips"
    __table_args__ = {"extend_existing": True}
    trip_id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, index=True)
    combined_route = Column(ARRAY(String))
    sherpa = Column(String)
    status = Column(String, index=True)
    next_idx_aug = Column(Integer)
    trips = relationship("IESBookingReq", back_populates="combined_trip")


class IESStations(Base):
    __tablename__ = "ies_stations"
    __table_args__ = {"extend_existing": True}
    id = Column(Integer, primary_key=True, index=True)
    ies_name = Column(String, unique=True, index=True)
    ati_name = Column(String, unique=True, index=True)
    pose = Column(ARRAY(Float))
