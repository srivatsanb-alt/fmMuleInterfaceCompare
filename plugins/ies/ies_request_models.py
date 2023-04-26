from models.request_models import ClientReq


class IesStation(ClientReq):
    ati_name: str
    ies_name: str

class EnableDisableSherpaReq(ClientReq):
    sherpa_name: str
    enable: bool

class EnableDisableRouteReq(ClientReq):
    tag: str
    enable: bool