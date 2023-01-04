from pydantic import BaseModel
from dataclasses import dataclass
from typing import List, Optional, Union
from models.base_models import JsonMixin


@dataclass
class FleetSherpa(JsonMixin):
    name: str
    api_key: Union[str, None]
    hwid: str
    fleet_name: str


@dataclass
class Fleet(JsonMixin):
    name: str
    map_name: Optional[str]


@dataclass
class FrontendUser(JsonMixin):
    name: str
    role: str


@dataclass
class BasicConfig(JsonMixin):
    customer: str
    location: str
    site: str
    fleet_names: List[str]
    all_server_ips: Optional[List[str]]
    mode: Optional[str] = "default"
    sherpa_port: Optional[str] = "5000"
    http_scheme: str = "https"
    handler_package: str = "handlers.default.handlers"
    handler_class: str = "handlers"


# frontenduser: List[FrontendUsers]
# fleets: List[Fleet]
# fleet_sherpas: List[FleetSherpas]
