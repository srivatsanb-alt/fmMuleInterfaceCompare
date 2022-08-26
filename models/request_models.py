from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Union, Dict

import pydantic


from core.constants import MessageType
from pydantic import BaseModel
from models.base_models import JsonMixin


class HitchReq(BaseModel):
    hitch: bool


class DirectionEnum(str, Enum):
    send = "send"
    receive = "receive"


class VisaType(str, Enum):
    PARKING = "parking"
    EXCLUSIVE_PARKING = "exclusive_parking"
    UNPARKING = "unparking"
    TRANSIT = "transit"


class AccessType(str, Enum):
    REQUEST = "request"
    RELEASE = "release"


class ConveyorReq(BaseModel):
    direction: DirectionEnum
    num_units: int


class DispatchButtonReq(BaseModel):
    value: bool


@pydantic.dataclasses.dataclass
class VisaReq:
    zone_id: str
    zone_name: str
    visa_type: VisaType


#################################################
# Messages from sherpas


class SherpaReq(BaseModel):
    source: Union[str, None] = None
    type: str
    timestamp: float


class InitExtraInfo(BaseModel):
    display_name: str
    ip_address: str
    chassis_number: str


class InitMsg(SherpaReq):
    current_pose: List[float]
    extra_info: Union[InitExtraInfo, None] = None
    type = MessageType.INIT


class ReachedReq(SherpaReq):
    trip_id: int
    trip_leg_id: int
    destination_pose: List[float]
    destination_name: str
    type = MessageType.REACHED


class SherpaPeripheralsReq(SherpaReq):
    auto_hitch: HitchReq = None
    conveyor: ConveyorReq = None
    dispatch_button: DispatchButtonReq = None
    error_info: str = None
    type = MessageType.PERIPHERALS


class ResourceReq(SherpaReq):
    visa: VisaReq = None
    # TODO: define types for these
    parking_slot: str = None
    charging_bay: str = None
    access_type: AccessType = None
    type = MessageType.RESOURCE_ACCESS


#################################################
# Messages from sherpas (Websocket)


@dataclass
class SherpaStatusMsg(JsonMixin):
    timestamp: float
    sherpa_name: str
    current_pose: List[float]
    battery_status: float
    mode: str
    error: bool = None
    error_info: str = None
    type: str = MessageType.SHERPA_STATUS


@dataclass
class StoppageInfo(JsonMixin):
    local_obstacle: List[float]
    time_elapsed_stoppages: float
    time_elapsed_obstacle_stoppages: float
    time_elapsed_visa_stoppages: float
    time_elapsed_other_stoppages: float


@dataclass
class Stoppages(JsonMixin):
    type: str
    extra_info: StoppageInfo


@dataclass
class TripInfo(JsonMixin):
    current_pose: List[float]
    destination_pose: List[float]
    destination_name: str
    eta_at_start: float
    eta: float
    progress: float
    stoppages: Stoppages = None


@dataclass
class TripStatusMsg(JsonMixin):
    timestamp: float
    trip_id: int
    trip_leg_id: int
    trip_info: TripInfo
    type: str = MessageType.TRIP_STATUS


#################################################
# Messages from frontend


class MasterDataInfo(BaseModel):
    fleet_name: str


class UserLogin(BaseModel):
    name: str
    password: str


class TripsReq(BaseModel):
    type: str


class TripMsg(BaseModel):
    route: List[str]
    tasks: Optional[Dict[str, str]] = None
    priority: Optional[int] = 0
    metadata: Optional[Dict[str, str]] = None


class BookingReq(TripsReq):
    trips: List[TripMsg]
    type: str = MessageType.BOOKING


class StartStopCtrlReq(BaseModel):
    start: bool


class PauseResumeCtrlReq(BaseModel):
    pause: bool


class SwitchModeCtrlReq(BaseModel):
    mode: str


class ResetPoseCtrlReq(BaseModel):
    fleet_station: str


#################################################
# Messages to sherpas


class FMReq(BaseModel):
    endpoint: str


class InitReq(FMReq):
    endpoint: str = "init"


class MoveReq(FMReq):
    endpoint: str = "move_to"
    trip_id: int
    trip_leg_id: int
    destination_pose: List[float]
    destination_name: str


class PeripheralsReq(FMReq):
    endpoint: str = "peripherals"
    auto_hitch: Optional[HitchReq]
    conveyor: Optional[ConveyorReq]


class PauseResumeReq(FMReq):
    endpoint: str = "pause_resume"
    pause: bool
    sherpa_name: str
    type = MessageType.PASS_TO_SHERPA


class SwitchModeReq(FMReq):
    endpoint: str = "switch_mode"
    mode: str
    sherpa_name: str
    type = MessageType.PASS_TO_SHERPA


class ResetPoseReq(FMReq):
    endpoint: str = "reset_pose"
    pose: List[float]
    sherpa_name: str
    type = MessageType.PASS_TO_SHERPA


class DiagnosticsReq(FMReq):
    endpoint: str = "diagnostics"
    sherpa_name: str
    type = MessageType.PASS_TO_SHERPA


@dataclass
class MapFileInfo(JsonMixin):
    file_name: str
    hash: str


@dataclass
class VerifyFleetFilesResp(JsonMixin):
    fleet_name: str
    files_info: List[MapFileInfo]


@dataclass
class ResourceResp(JsonMixin):
    granted: bool
    visa: VisaReq = None
    parking_slot = None
    charging_bay = None
    access_type: AccessType = None


@dataclass
class InitResp(JsonMixin):
    display_name: str
    hwid: str
