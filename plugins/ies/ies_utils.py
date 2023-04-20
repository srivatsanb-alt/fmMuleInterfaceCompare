from dataclasses import dataclass
import json
import os

from models.base_models import JsonMixin
from models.trip_models import TripStatus

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
class StationIES(JsonMixin):
    messageType: str
    ati_name: str
    ies_name: str
