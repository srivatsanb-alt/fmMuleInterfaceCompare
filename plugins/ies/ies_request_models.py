from models.request_models import ClientReq


class IesStation(ClientReq):
    ati_name: str
    ies_name: str
