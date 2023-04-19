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
        engine = create_engine(os.path.join(os.getenv("FM_DATABASE_URI"), "plugin_ies_v2"))
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


class JobIES(Base):
    __tablename__ = "job_ies"
    __table_args__ = {"extend_existing": True}
    ext_ref_id = Column(String, primary_key=True, index=True)
    route = Column(ARRAY(String))
    status = Column(String)
    kanban_id = Column(String, index=True)
    other_info = Column(JSONB)
    combined_trip_id = Column(ForeignKey("combined_trips_v2.trip_id"))
    combined_trip = relationship(
        "plugins.ies_v2.ies_v2_models.CombinedTripsv2",
        back_populates="trips",
        uselist=False,
    )


class CombinedTripsv2(Base):
    __tablename__ = "combined_trips_v2"
    __table_args__ = {"extend_existing": True}
    trip_id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, index=True)
    combined_route = Column(ARRAY(String))
    status = Column(String, index=True)
    next_idx_aug = Column(Integer)
    trips = relationship(
        "plugins.ies_v2.ies_v2_models.JobIES", back_populates="combined_trip"
    )
    sherpa = Column(String)
