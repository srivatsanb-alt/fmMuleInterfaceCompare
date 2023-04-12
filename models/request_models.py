from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Union, Dict
import pydantic


from core.constants import MessageType
from pydantic import BaseModel
from models.base_models import JsonMixin
from models.config_models import (
    BasicConfig,
    OptimalDispatch,
    Alerts,
)


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
    SEZ = "sez"


class AccessType(str, Enum):
    REQUEST = "request"
    RELEASE = "release"


class ConveyorReq(BaseModel):
    direction: DirectionEnum
    num_units: int
    ack: Optional[bool]


class SpeakerReq(BaseModel):
    sound: SoundEnum
    play: bool


class IndicatorReq(BaseModel):
    pattern: PatternEnum
    activate: bool


class DispatchButtonReq(BaseModel):
    value: bool
    timeout: Optional[float]


@pydantic.dataclasses.dataclass
class VisaReq:
    zone_id: str
    zone_name: str
    visa_type: VisaType


#################################################
# Messages from sherpas


class ErrInfo(BaseModel):
    err_code: str
    module: Optional[str] = None
    sub_module: Optional[str] = None
    err_msg: str
    err_disp_msg: Optional[str] = None
    recovery_msg: Optional[str] = None
    other_info: Optional[dict] = None


class SherpaReq(BaseModel):
    source: Union[str, None] = None
    type: str
    timestamp: float


class WSResp(BaseModel):
    success: bool
    response: Optional[Dict[str, Union[str, int, float, dict, None]]]


class InitExtraInfo(BaseModel):
    display_name: str
    ip_address: str
    chassis_number: str


class InitMsg(SherpaReq):
    current_pose: List[float]
    extra_info: Union[InitExtraInfo, None] = None
    type = MessageType.INIT


class SherpaAlertMsg(SherpaReq):
    trolley_load_cell: Union[str, None]
    low_battery_alarm: Union[str, None]
    obstructed: Union[str, None]
    emergency_button: Union[str, None]
    user_pause: Union[str, None]
    type = MessageType.SHERPA_ALERTS


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
    source: str = "self"
    sherpa_name: str = None
    type: str = MessageType.ASSIGN_NEXT_TASK


class FMHealthCheck(BaseModel):
    source: str = "self"
    type: str = MessageType.FM_HEALTH_CHECK


#################################################
# Messages from frontend
class ClientReq(BaseModel):
    source: Union[str, None] = None


class MasterDataInfo(ClientReq):
    fleet_name: str


class UserLogin(ClientReq):
    name: str
    password: str


class AddEditSherpaReq(ClientReq):
    api_key: str
    hwid: str
    fleet_name: str


class AddFleetReq(ClientReq):
    site: str
    location: str
    customer: str
    map_name: str


class FleetConfigUpdate(BaseModel):
    fleet: BasicConfig
    optimal_dispatch: OptimalDispatch
    alerts: Optional[Alerts]


class TripMetaData(BaseModel):
    metadata: Dict[str, str]


class TripsReq(ClientReq):
    type: str


class TripMsg(ClientReq):
    route: List[str]
    priority: Optional[float] = 1.0
    tasks: Optional[Dict[str, str]] = None
    metadata: Optional[Dict[str, Union[str, None]]] = None


class RoutePreview(ClientReq):
    route: List[str]


class LiveRoute(ClientReq):
    sherpa_name: str


class BookingReq(ClientReq):
    trips: List[TripMsg]
    type: str = MessageType.BOOKING


class DeleteOngoingTripReq(ClientReq):
    booking_id: int
    type: str = MessageType.DELETE_ONGOING_TRIP


class DeleteBookedTripReq(ClientReq):
    booking_id: int
    type: str = MessageType.DELETE_BOOKED_TRIP


class SherpaInductReq(ClientReq):
    induct: bool
    sherpa_name: Optional[str]
    type: str = MessageType.INDUCT_SHERPA


class StartStopCtrlReq(ClientReq):
    start: bool


class PauseResumeCtrlReq(ClientReq):
    pause: bool


class SwitchModeCtrlReq(ClientReq):
    mode: str


class ResetPoseCtrlReq(ClientReq):
    fleet_station: str


class SherpaImgUpdateCtrlReq(ClientReq):
    sherpa_name: str
    type: str = "sherpa_img_update"


class TripStatusReq(ClientReq):
    booked_from: Optional[str]
    booked_till: Optional[str]
    trip_ids: Optional[List[int]]


class GiveRouteWPS(ClientReq):
    start_pose: List = None  # Start station pose
    to_poses: List = None  # end station pose(s). can be more than 1 station
    sherpa_name: str = None  # only for Live monitoring: Route from current pose to next destination, None for route-preview


class DeleteVisaAssignments(ClientReq):
    type: str = MessageType.DELETE_VISA_ASSIGNMENTS


class DeleteOptimalDispatchAssignments(ClientReq):
    type: str = MessageType.DELETE_OPTIMAL_DISPATCH_ASSIGNMENTS
    fleet_name: str


class GetFMIncidents(ClientReq):
    sherpa_name: str


#################################################
# Messages to sherpas


class FMReq(BaseModel):
    source: Union[str, None] = None
    endpoint: str


class InitReq(FMReq):
    endpoint: str = "init"


class ResetVisasHeldReq(FMReq):
    endpoint: str = "reset_visas_held"


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
    dispatch_button: Optional[DispatchButtonReq]


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
    image_tag: str
    fm_server_username: str
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
