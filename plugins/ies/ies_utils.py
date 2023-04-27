from dataclasses import dataclass
import json
import os
import logging

from models.base_models import JsonMixin
from models.trip_models import TripStatus
import plugin_comms as pcomms

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


def get_all_ies_routes(fleet_name):
    status_code, all_saved_routes = pcomms.send_req_to_FM(
        "plugin_ies", "get_saved_routes", "get", query=fleet_name
    )
    if not status_code == 200:
        logger.info(f"couldn't get saved routes for fleet {fleet_name}")
        return {}
    ies_routes = {}
    for route_tag, route_info in all_saved_routes.items():
        if "ies" in route_info["other_info"].keys():
            if route_info["other_info"]["ies"]:
                ies_routes.update({route_tag: route_info["route"]})
    return ies_routes


def get_exclude_stations_sherpa(sherpa_name, fleet_name):
    status_code, all_saved_routes = pcomms.send_req_to_FM(
        "plugin_ies", "get_saved_routes", "get", query=fleet_name
    )
    if not status_code == 200:
        logger.info(f"couldn't get saved routes for fleet {fleet_name}")
        return []
    exclude_stations = []
    for route_tag, route_info in all_saved_routes.items():
        if route_tag == f"exclude_stations_{sherpa_name}":
            exclude_stations = route_info["route"]
    return exclude_stations


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
