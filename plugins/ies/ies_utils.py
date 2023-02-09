import sys
import os
from sqlalchemy import Integer, String, Column, ARRAY
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from dataclasses import dataclass
from utils.util import str_to_dt, str_to_dt_UTC, dt_to_str
from plugins.plugin_comms import send_req_to_FM
from models.trip_models import TripStatus

sys.path.append("/app")
from models.base_models import Base, TimestampMixin
from models.base_models import JsonMixin

IES_JOB_STATUS_MAPPING = {
    TripStatus.BOOKED: "ACCEPTED",
    TripStatus.ASSIGNED: "SCHEDULED",
    TripStatus.EN_ROUTE: "IN_PROGRESS",
    TripStatus.WAITING_STATION: "IN_PROGRESS",
    TripStatus.SUCCEEDED: "COMPLETED",
    TripStatus.FAILED: "FAILED",
    TripStatus.CANCELLED: "CANCELLED",
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


def run_query(db_table, field, query):
    return session.query(db_table).filter(field == query).one_or_none()


# IES DB models
class TripsIES(Base, TimestampMixin):
    __tablename__ = "trips_ies"
    __table_args__ = {"extend_existing": True}
    id = Column(Integer, primary_key=True)
    trip_id = Column(Integer, unique=True)
    booking_id = Column(Integer, unique=True)
    externalReferenceId = Column(String, unique=True)
    status = Column(String)
    actions = Column(ARRAY(String))
    locations = Column(ARRAY(String))


class IESMessages:
    # messages from IES to FM
    job_query = "JobQuery"
    job_create = "JobCreate"
    job_update = "JobUpdate"
    job_cancel = "JobCancel"
    job_cancel_response = "JobCancelResponse"

    # messages from FM to IES
    agv_fault = "AgvFault"
    agv_update = "AgvUpdate"


engine = create_engine(os.path.join(os.getenv("FM_DATABASE_URI"), "plugin_ies"))
session_maker = sessionmaker(autocommit=False, autoflush=True, bind=engine)
session = session_maker()

