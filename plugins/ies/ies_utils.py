import sys
import os
import time
import redis
import logging
import json
from typing import Dict
from sqlalchemy import Integer, String, Column, ARRAY
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from dataclasses import dataclass
from utils.util import str_to_dt, str_to_dt_UTC, dt_to_str
from plugins.plugin_comms import send_req_to_FM
from models.trip_models import TripStatus
from utils.util import get_table_as_dict

sys.path.append("/app")
from models.base_models import Base, TimestampMixin
from models.base_models import JsonMixin
from models.fleet_models import Sherpa, SherpaStatus, StationStatus, Fleet, Station

logger = logging.getLogger("plugin_ies")

IES_JOB_STATUS_MAPPING = {
    TripStatus.BOOKED: "ACCEPTED",
    TripStatus.ASSIGNED: "SCHEDULED",
    TripStatus.EN_ROUTE: "IN_PROGRESS",
    TripStatus.WAITING_STATION: "IN_PROGRESS",
    TripStatus.SUCCEEDED: "COMPLETED",
    TripStatus.FAILED: "FAILED",
    TripStatus.CANCELLED: "CANCELLED",
}

locationID_station_mapper_path = os.path.join(
    os.getenv("FM_MAP_DIR"), "plugin_ies", "locationID_station_mapping.json"
)
with open(locationID_station_mapper_path, "r") as f:
    locationID_station_mapping = json.load(f)


def get_locationID_station_mapping():
    return locationID_station_mapping


def get_ati_station_name(bosch_station_name):
    return locationID_station_mapping[bosch_station_name]["ati_name"]


def get_ati_pos_index(bosch_station_name):
    return int(locationID_station_mapping[bosch_station_name]["pos_index"])


def get_ati_station_details(bosch_station_name):
    details = (
        locationID_station_mapping[bosch_station_name]["ati_name"],
        locationID_station_mapping[bosch_station_name]["pos_index"],
    )
    return details


def get_end_station(line_name):
    if line_name.lower() == "ecfa":
        key = "ECFA_end_station"
    end_station = locationID_station_mapping["metadata"][key]
    return end_station


def remove_from_pending_jobs_db(redis_db, ext_ref_id):
    jobs_list = read_dict_var_from_redis_db(redis_db, "pending_jobs")
    if ext_ref_id in jobs_list.keys():
        jobs_list.pop(ext_ref_id)
    redis_db.set("pending_jobs", json.dumps(jobs_list))
    return


def add_to_ongoing_trips_db(redis_db, trip_id, current_ext_ref_ids, destination_stations):
    ongoing_trips = read_dict_var_from_redis_db(redis_db, "ongoing_trips")
    ongoing_trips.update({trip_id: {"ref_ids": current_ext_ref_ids, "destination_stations": destination_stations}})
    redis_db.set("ongoing_trips", json.dumps(ongoing_trips))
    return


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


def run_query(db_table, field, query):
    return session.query(db_table).filter(field == query).one_or_none()


def read_dict_var_from_redis_db(db: redis.Redis, entry: str) -> Dict:
    """Reads a list variable from redis db, returns default value if variable not exists or corrupted!"""
    db_value = db.get(entry)
    logger.info(f"got redis db_value {db_value} for {entry}!")
    if (db_value is None) or (not db_value) or (db_value == b"null") or (db_value == b"[]"):
        return {}
    return json.loads(db_value)


def get_fleet_status_msg(session, fleet):
    msg = {}
    all_station_status = session.get_all_station_status()
    all_sherpa_status = session.get_all_sherpa_status()

    sherpa_status_update = {}
    station_status_update = {}

    if all_sherpa_status:
        logger.info(f"All sherpa status: {all_sherpa_status}")
        for sherpa_status in all_sherpa_status:
            logger.info(f"sherpa status: {sherpa_status}")
            logger.info(f"fleet: {fleet.name}")
            if sherpa_status.sherpa.fleet.name == fleet.name:
                sherpa_status_update.update(
                    {
                        sherpa_status.sherpa_name: get_table_as_dict(
                            SherpaStatus, sherpa_status
                        )
                    }
                )

                sherpa_status_update[sherpa_status.sherpa_name].update(
                    get_table_as_dict(Sherpa, sherpa_status.sherpa)
                )

    if all_station_status:
        for station_status in all_station_status:
            if station_status.station.fleet.name == fleet.name:
                station_status_update.update(
                    {
                        station_status.station_name: get_table_as_dict(
                            StationStatus, station_status
                        )
                    }
                )

                station_status_update[station_status.station_name].update(
                    get_table_as_dict(Station, station_status.station)
                )

    msg.update({"sherpa_status": sherpa_status_update})
    msg.update({"station_status": station_status_update})
    msg.update({"fleet_status": get_table_as_dict(Fleet, fleet)})
    msg.update({"fleet_name": fleet.name})
    msg.update({"type": "fleet_status"})
    msg.update({"timestamp": time.time()})
    return msg
