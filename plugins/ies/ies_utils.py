import sys
from sqlalchemy import Integer, String, Column, ARRAY
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
import os
from dataclasses import dataclass

sys.path.append("/app")
from models.base_models import Base, TimestampMixin
from models.base_models import JsonMixin


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
