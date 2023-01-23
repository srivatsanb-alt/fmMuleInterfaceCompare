from dataclasses import dataclass
from typing import List, Optional, Union, Dict
from models.base_models import JsonMixin


@dataclass
class FleetSherpa(JsonMixin):
    name: str
    api_key: Union[str, None]
    hwid: str
    fleet_name: str


@dataclass
class Fleets(JsonMixin):
    name: str
    map_name: Optional[str]


@dataclass
class FrontendUser(JsonMixin):
    name: str
    role: str
    hashed_password: str


@dataclass
class Comms(JsonMixin):
    mule_heartbeat_interval: int = 60


@dataclass
class Simulator(JsonMixin):
    simulate: bool = False
    book_trips: bool = False


@dataclass
class Stations(JsonMixin):
    dispatch_timeout: float = 10.0


@dataclass
class OptimalDispatch(JsonMixin):
    method: str = "hungarian"
    prioritise_waiting_stations: bool = True
    eta_power_factor: float = 1.0
    priority_power_factor: float = 0.1


@dataclass
class Alerts(JsonMixin):
    slack_webhook_url: Optional[str]
    time_interval: Optional[float] = 30.0
    notifications: Optional[bool] = False


@dataclass
class RQ(JsonMixin):
    default_job_timeout: Optional[int] = 15
    generic_handler_job_timeout: Optional[int] = 10


@dataclass
class BasicConfig(JsonMixin):
    customer: str
    location: str
    site: str
    fleet_names: List[str]
    comms: Comms
    simulator: Simulator
    all_server_ips: List[str]
    rq: Optional[RQ] = None
    stations: Optional[Stations] = None
    fleet_map_mapping: Optional[Dict[str, str]] = None
    map_names: Optional[List[str]] = None
    mode: Optional[str] = "default"
    sherpa_port: Optional[str] = "5000"
    http_scheme: str = "https"
    handler_package: str = "handlers.default.handlers"
    handler_class: str = "handlers"
