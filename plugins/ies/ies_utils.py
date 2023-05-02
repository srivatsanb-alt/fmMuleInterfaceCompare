from dataclasses import dataclass
import json
import os
import logging
import datetime

from models.base_models import JsonMixin
from models.trip_models import TripStatus
import plugin_comms as pcomms
import plugins.ies.ies_models as im

logger = logging.getLogger("plugin_ies")

TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
IES_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"

IES_JOB_STATUS_MAPPING = {
    TripStatus.BOOKED: "ACCEPTED",
    TripStatus.ASSIGNED: "SCHEDULED",
    TripStatus.EN_ROUTE: "IN_PROGRESS",
    TripStatus.WAITING_STATION: "IN_PROGRESS",
    TripStatus.SUCCEEDED: "COMPLETED",
    TripStatus.FAILED: "FAILED",
    TripStatus.CANCELLED: "CANCELLED",
}


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


def get_ies_station(dbsession, ati_station_name=None, ies_station_name=None):
    if ati_station_name:
        return (
            dbsession.session.query(im.IESStations)
            .filter(im.IESStations.ati_name == ati_station_name)
            .one_or_none()
        )
    elif ies_station_name:
        return (
            dbsession.session.query(im.IESStations)
            .filter(im.IESStations.ies_name == ies_station_name)
            .one_or_none()
        )
    return None


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


def dt_to_str(dt):
    return datetime.datetime.strftime(dt, TIME_FORMAT)


def str_to_dt(dt_str):
    return datetime.datetime.strptime(dt_str, TIME_FORMAT)


def str_to_dt_UTC(dt_str):
    return datetime.datetime.strptime(dt_str, IES_TIME_FORMAT + " %z")


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
