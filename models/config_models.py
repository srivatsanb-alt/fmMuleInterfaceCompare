from dataclasses import dataclass
from typing import Optional, Dict, List
from models.base_models import JsonMixin


@dataclass
class Comms(JsonMixin):
    mule_heartbeat_interval: int = 60


@dataclass
class Simulator(JsonMixin):
    simulate: bool = False
    book_trips: bool = False
    visa_handling: bool = False
    speedup_factor: float = 1.0
    average_velocity: float = 0.8
    routes: Optional[Dict] = None
    initialize_sherpas_at: Optional[Dict] = None


@dataclass
class Stations(JsonMixin):
    dispatch_timeout: float = 10.0


@dataclass
class OptimalDispatch(JsonMixin):
    method: str = "hungarian"
    prioritise_waiting_stations: bool = True
    eta_power_factor: float = 1.0
    priority_power_factor: float = 0.1
    exclude_stations: Optional[Dict] = None


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
    comms: Comms
    simulator: Simulator
    all_server_ips: List[str]
    rq: Optional[RQ] = None
    stations: Optional[Stations] = None
    mode: Optional[str] = "default"
    sherpa_port: Optional[str] = "5000"
    http_scheme: str = "https"
    handler_package: str = "handlers.default.handlers"
    handler_class: str = "handlers"
