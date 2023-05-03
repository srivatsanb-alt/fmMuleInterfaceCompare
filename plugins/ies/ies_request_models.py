from models.request_models import ClientReq
from typing import List


class IesStation(ClientReq):
    ati_name: str
    ies_name: str


class EnableDisableSherpaReq(ClientReq):
    sherpa_name: str
    enable: bool


class EnableDisableRouteReq(ClientReq):
    tag: str
    enable: bool


class ConsolidationInfoReq(ClientReq):
    sherpa_name: str
    route_tag: str
    start_station: str


class ConsolidateBookReq(ClientReq):
    ext_ref_ids: List[str]
    route_tag: str
