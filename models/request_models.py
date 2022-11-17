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


class SoundEnum(str, Enum):
    wait_for_dispatch = "wait_for_dispatch"
    free = "free"
    pause = "pause"


class PatternEnum(str, Enum):
    wait_for_dispatch = "wait_for_dispatch"
    free = "free"
    pause = "pause"
    default = "default"


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


class SpeakerReq(BaseModel):
    sound: SoundEnum
    play: bool


class IndicatorReq(BaseModel):
    pattern: PatternEnum
    activate: bool


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
    speaker: SpeakerReq = None
    indicator: IndicatorReq = None
    error_device: str = None
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
class SherpaMsg(JsonMixin):
    source: str
    timestamp: float


@dataclass
class SherpaStatusMsg(SherpaMsg, JsonMixin):
    sherpa_name: str
    current_pose: List[float]
    battery_status: float
    mode: str
    error: bool = None
    error_info: str = None
    type: str = MessageType.SHERPA_STATUS


@dataclass
class StoppageInfo(JsonMixin):
    velocity_speed_factor: float
    obstacle_speed_factor: float
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
    total_route_length: float
    remaining_route_length: float
    cte: float
    te: float
    eta_at_start: float
    eta: float
    progress: float


@dataclass
class TripStatusMsg(SherpaMsg, JsonMixin):
    trip_id: int
    trip_leg_id: int
    trip_info: TripInfo
    stoppages: Stoppages = None
    type: str = MessageType.TRIP_STATUS


#################################################
# internal messsages FM to FM
class AssignNextTask(BaseModel):
    sherpa_name: str
    type: str = MessageType.ASSIGN_NEXT_TASK


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
    priority: Optional[float] = 1.0
    tasks: Optional[Dict[str, str]] = None
    metadata: Optional[Dict[str, Union[List[int], bool, str, int]]] = None


class RoutePreview(BaseModel):
    route: List[str]
    fleet_name: str


class BookingReq(TripsReq):
    trips: List[TripMsg]
    type: str = MessageType.BOOKING


class DeleteOngoingTripReq(BaseModel):
    booking_id: int
    type: str = MessageType.DELETE_ONGOING_TRIP


class DeleteBookedTripReq(BaseModel):
    booking_id: int
    type: str = MessageType.DELETE_BOOKED_TRIP


class SherpaInductReq(BaseModel):
    induct: bool
    sherpa_name: Optional[str]
    type: str = MessageType.INDUCT_SHERPA


class StartStopCtrlReq(BaseModel):
    start: bool


class PauseResumeCtrlReq(BaseModel):
    pause: bool


class SwitchModeCtrlReq(BaseModel):
    mode: str


class ResetPoseCtrlReq(BaseModel):
    fleet_station: str


class SherpaImgUpdateCtrlReq(BaseModel):
    sherpa_name: str
    type: str = "sherpa_img_update"


class TripStatusReq(BaseModel):
    booked_from: Optional[str]
    booked_till: Optional[str]
    trip_ids: Optional[List[int]]


class GiveRouteWPS(BaseModel):
    start_pose: List = None  # Start station pose
    to_poses: List = None  # end station pose(s). can be more than 1 station
    sherpa_name: str = None  # only for Live monitoring: Route from current pose to next destination, None for route-preview


class DeleteVisaAssignments(BaseModel):
    type: str = MessageType.DELETE_VISA_ASSIGNMENTS


class DeleteOptimalDispatchAssignments(BaseModel):
    type: str = MessageType.DELETE_OPTIMAL_DISPATCH_ASSIGNMENTS
    fleet_name: str


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


class TerminateTripReq(FMReq):
    endpoint: str = "terminate_trip"
    trip_id: int
    trip_leg_id: int


class PeripheralsReq(FMReq):
    endpoint: str = "peripherals"
    auto_hitch: Optional[HitchReq]
    conveyor: Optional[ConveyorReq]
    speaker: Optional[SpeakerReq]
    indicator: Optional[IndicatorReq]


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


class SherpaImgUpdate(FMReq):
    endpoint: str = "img_update"
    ip_address: str
    image_tag: str
    registry_port: str
    fm_host_name: str
    time_zone: str


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


#################################################
# Messages to frontend
@dataclass
class TripStatusUpdate(JsonMixin):
    sherpa_name: str
    fleet_name: str
    trip_id: int
    trip_leg_id: int
    trip_info: TripInfo
    stoppages: Stoppages = None
    type: str = MessageType.TRIP_STATUS


@dataclass
class RouteWPS(JsonMixin):
    route_wps: List
