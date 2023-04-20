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


class IESBookingReq(Base):
    __tablename__ = "ies_booking_req"
    __table_args__ = {"extend_existing": True}
    ext_ref_id = Column(String, primary_key=True, index=True)
    start_station = Column(String)
    route = Column(ARRAY(String))
    status = Column(String)
    kanban_id = Column(String, index=True)
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
