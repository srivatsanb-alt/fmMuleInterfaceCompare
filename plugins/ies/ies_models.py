import os
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine
from sqlalchemy import Integer, String, Column, ARRAY, Boolean
from dataclasses import dataclass
from models.base_models import Base, JsonMixin
from sqlalchemy.dialects.postgresql import JSONB


class DBSession:
    def __init__(self):
        engine = create_engine(
            os.path.join(os.getenv("FM_DATABASE_URI"), "plugin_ies")
        )
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

    def query_trip_id(self, trip_id):
        return self.session.query(TripsIES).filter(TripsIES.trip_id == trip_id).one_or_none()


    def query_ref_id(self, ref_id):
        return (
            self.session.query(TripsIES).filter(TripsIES.externalReferenceId == ref_id).one_or_none()
        )


class TripsIES(Base):
    __tablename__ = "trips_ies"
    __table_args__ = {"extend_existing": True}
    id = Column(Integer, primary_key=True)
    trip_id = Column(Integer, unique=True)
    booking_id = Column(Integer, unique=True)
    externalReferenceId = Column(String, unique=True)
    status = Column(String)
    actions = Column(ARRAY(String))
    locations = Column(ARRAY(String))
    combined = Column(Boolean)
    ongoing = Column(Boolean)
    # destination_stations = Column(ARRAY(String))
    # ref_ids = Column(ARRAY(String))
    combined_trip_data = Column(JSONB)



class PendingJobsIES(Base):
    __tablename__ = "pending_jobs_ies"
    __table_args__ = {"extend_existing": True}
    externalReferenceId = Column(String, unique=True, primary_key = True)
    tasklist = Column(ARRAY(JSONB))
    priority = Column(Integer)


@dataclass
class AGVMsg(JsonMixin):
    messageType: str
    externalReferenceId: str
    vehicleId: str
    vehicleTypeID: str

    def to_dict(self):
        return {
            "messageType": self.messageType,
            "externalReferenceId": self.externalReferenceId,
            "vehicleId": self.vehicleId,
            "vehicleTypeID": self.vehicleTypeID,
        }


@dataclass
class MsgToIES(JsonMixin):
    messageType: str
    externalReferenceId: str
    jobStatus: str

    def to_dict(self):
        return {
            "messageType": self.messageType,
            "externalReferenceId": self.externalReferenceId,
            "jobStatus": self.jobStatus,
        }


@dataclass
class JobCreate(JsonMixin):
    messageType: str
    externalReferenceId: str
    taskList: list
    priority: int = 1
    jobStatus = str


@dataclass
class JobCancel(JsonMixin):
    messageType: str
    externalReferenceId: str
    jobStatus: str


@dataclass
class JobQuery(JsonMixin):
    messageType: str
    since: str
    until: str