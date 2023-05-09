from dataclasses import dataclass
import json
import os
import logging
import datetime
import redis

from models.base_models import JsonMixin
from models.trip_models import TripStatus
import plugins.plugin_comms as pcomms
import plugins.ies.ies_models as im

logger = logging.getLogger("plugin_ies")

TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
IES_TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
IES_TIME_FORMAT_QUERY = "%Y-%m-%dT%H:%M:%S.%f"

IES_JOB_STATUS_MAPPING = {
    "pending": "WAITING_FOR_CONSOLIDATION",
    TripStatus.BOOKED: "ACCEPTED",
    TripStatus.ASSIGNED: "SCHEDULED",
    TripStatus.EN_ROUTE: "IN_PROGRESS",
    TripStatus.WAITING_STATION: "IN_PROGRESS",
    TripStatus.SUCCEEDED: "COMPLETED",
    TripStatus.FAILED: "FAILED",
    TripStatus.CANCELLED: "CANCELLED",
}


def send_msg_to_ies(msg):
    pub = redis.from_url(os.getenv("FM_REDIS_URI"), decode_responses=True)
    pub.publish("channel:plugin_ies", str(msg))


def populate_ies_info():
    with im.DBSession() as dbsession:
        info_db = dbsession.session.query(im.IESInfo).all()
        if info_db == []:
            info = im.IESInfo(consolidate=True, ies_version=2.0)
            dbsession.session.add(info)


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
    exclude_stations = []
    status_code, all_saved_routes = pcomms.send_req_to_FM(
        "plugin_ies", "get_saved_routes_backend", "get", query=fleet_name
    )
    if not status_code == 200:
        logger.info(f"couldn't get saved routes for fleet {fleet_name}")

    for route_tag, route_info in all_saved_routes.items():
        if route_tag == f"exclude_stations_{sherpa_name}":
            exclude_stations.extend(route_info["route"])
    return exclude_stations


def get_sherpa_summary_for_sherpa(sherpa_name):
    status_code, sherpa_summary_response = pcomms.send_req_to_FM(
        "plugin_ies", "sherpa_summary", req_type="get", query=sherpa_name
    )
    if status_code != 200:
        raise ValueError(f"sherpa summary req. failed for sherpa {sherpa_name}")
    return sherpa_summary_response


def get_saved_route(route_tag):
    status_code, saved_route = pcomms.send_req_to_FM(
        "plugin_ies", "get_saved_route", "get", query=route_tag
    )
    if status_code != 200:
        raise ValueError(f"can't get route from FM for tag {route_tag}")
    route = im.IESRoutes(route_tag=route_tag, route=saved_route["route"])
    return route


def get_last_completed_task_msg(last_completed_task):
    return {
        "ActionName": "",
        "LocationId": str(last_completed_task),
    }


def compose_and_send_job_update_msg(ext_ref_id, status, route, next_idx_aug):
    logger.info(f"sending JobUpdates...{ext_ref_id}")
    msg_to_ies = MsgToIES("JobUpdate", ext_ref_id, IES_JOB_STATUS_MAPPING[status]).to_dict()
    last_completed_task = None if next_idx_aug == 0 else route[next_idx_aug - 1]
    msg_to_ies.update(
        {
            "ActionName": "",
            "LocationId": str(last_completed_task),
        }
    )
    send_msg_to_ies(msg_to_ies)


def dt_to_str(dt):
    return datetime.datetime.strftime(dt, TIME_FORMAT)


def str_to_dt(dt_str):
    return datetime.datetime.strptime(dt_str, TIME_FORMAT)


def str_to_dt_UTC(dt_str, query: bool = False):
    if not query:
        return datetime.datetime.strptime(dt_str, IES_TIME_FORMAT + " %z")
    return datetime.datetime.strptime(dt_str, IES_TIME_FORMAT_QUERY + " %z")


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
class JobQuery(JsonMixin):
    messageType: str
    since: str
    until: str


@dataclass
class JobCancel(JsonMixin):
    messageType: str
    externalReferenceId: str


@dataclass
class StationIES(JsonMixin):
    messageType: str
    ati_name: str
    ies_name: str


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
