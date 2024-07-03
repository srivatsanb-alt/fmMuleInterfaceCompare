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
    UNPARKING = "unparking"
    TRANSIT = "transit"


class AccessType(str, Enum):
    REQUEST = "request"
    RELEASE = "release"


class PasstoSherpaEndpoints:
    RESET_POSE = "reset_pose"
    DIAGNOSTICS = "diagnostics"
    QUICK_DIAGNOSTICS = "quick_diagnostics"
    PAUSE_RESUME = "pause_resume"
    SWITCH_MODE = "switch_mode"
    IMG_UPDATE = "img_update"
    REVOKE_VISA = "revoke_visa"
    SOUND = "sound"
    CURRENT_SOUND_STATUS = "current_sound_status"
    RESET_POSE_VPR = 'reset_pose_vpr'


class SherpaType(str, Enum):
    tug = "tug"
    tug_lite = "tug_lite"
    lite = "lite"
    lifter = "lifter"
    pallet_mover = "pallet_mover"


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


class FrontendUserRoles:
    viewer = 0
    operator = 1
    supervisor = 2
    superuser = 3
    support = 4


#################################################
# Messages from sherpa
class SherpaReq(BaseModel):
    source: Union[str, None] = None
    type: str
    timestamp: float
    ttl: Optional[int] = None


class WSResp(BaseModel):
    success: bool
    response: Optional[Dict[str, Union[str, int, float, dict, None]]]
    ttl: Optional[int] = None


class InitExtraInfo(SherpaReq):
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
    ttl = 5
    type = MessageType.RESOURCE_ACCESS


# messages from sherpa not going to queue
class FileUploadReq(BaseModel):
    filename: str
    type: str
    fm_incident_id: Optional[str]


class AddFMIncidentReq(BaseModel):
    type: str
    code: str
    incident_id: str
    message: str
    data_uploaded: bool
    data_path: Optional[str] = None
    module: Optional[str] = None
    sub_module: Optional[str] = None
    display_message: Optional[str] = None
    recovery_message: Optional[str] = None
    error_code: Optional[str] = None
    other_info: Optional[dict] = None


class UpdateIncidentDataDetailsReq(BaseModel):
    incident_id: str
    data_uploaded: bool
    data_path: Optional[str]
    other_info: Optional[Dict[str, str]] = None


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
class InternalReq(BaseModel):
    source: Union[str, None] = None
    ttl: Optional[int] = None


class TriggerOptimalDispatch(InternalReq):
    fleet_name: str
    type: str = MessageType.TRIGGER_OPTIMAL_DISPATCH


class AssignNextTask(InternalReq):
    sherpa_name: str = None
    type: str = MessageType.ASSIGN_NEXT_TASK


class FMHealthCheck(InternalReq):
    type: str = MessageType.FM_HEALTH_CHECK


class MiscProcess(InternalReq):
    type: str = MessageType.MISC_PROCESS


#################################################
# Messages from frontend
class ClientReq(BaseModel):
    source: Union[str, None] = None
    ttl: Optional[int] = None


class GenericFromToTimeReq(ClientReq):
    from_dt: Optional[str]
    to_dt: Optional[str]


class MasterDataInfo(ClientReq):
    fleet_name: str


class UserLogin(ClientReq):
    name: str
    password: str


class FrontendUserDetails(ClientReq):
    name: str
    role: str
    password: Optional[str] = None


class AddEditSherpaReq(ClientReq):
    hwid: str
    fleet_name: str
    api_key: Optional[str]
    sherpa_type: SherpaType


class AddFleetReq(ClientReq):
    site: str
    location: str
    customer: str
    map_name: str


class UpdateMapReq(ClientReq):
    fleet_name: str
    map_path: str


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
    trip_id: Optional[int] = None


class DeleteBookedTripReq(ClientReq):
    booking_id: int
    type: str = MessageType.DELETE_BOOKED_TRIP
    trip_id: Optional[int] = None


class ForceDeleteOngoingTripReq(ClientReq):
    sherpa_name: str
    type: str = MessageType.FORCE_DELETE_ONGOING_TRIP


class SherpaInductReq(ClientReq):
    induct: bool
    sherpa_name: Optional[str]
    type: str = MessageType.INDUCT_SHERPA


class StartStopCtrlReq(ClientReq):
    start: bool
    maintenance: Optional[bool]
    fleet_name: Optional[str]
    type: str = MessageType.FLEET_START_STOP


class PauseResumeCtrlReq(ClientReq):
    pause: bool


class SwitchModeCtrlReq(ClientReq):
    mode: str


class ResetPoseCtrlReq(ClientReq):
    fleet_station: str


class SherpaImgUpdateCtrlReq(ClientReq):
    sherpa_name: str
    type: str = "sherpa_img_update"


class TripStatusReq(GenericFromToTimeReq):
    trip_ids: Optional[List[int]]


class TripStatusReq_pg(GenericFromToTimeReq):
    page_no: int
    rec_limit: int
    filter_fleets: List[str]
    filter_sherpa_names: Optional[List[str]]
    filter_status: Optional[List[str]]
    sort_field: Optional[str]
    sort_order: Optional[str]
    search_txt: Optional[str]


class GiveRouteWPS(ClientReq):
    start_pose: List = None  # Start station pose
    to_poses: List = None  # end station pose(s). can be more than 1 station
    sherpa_name: str = None  # only for Live monitoring: Route from current pose to next destination, None for route-preview


class GetFMIncidents(ClientReq):
    sherpa_name: str
    num_of_incidents: int = 1
    historic: Optional[bool] = False


class FMIncidentsReqPg(ClientReq):
    from_dt: str
    to_dt: str
    error_type: Optional[str] = "fm_error"
    sort_field: Optional[str] = "created_at"
    sort_order: Optional[str] = "desc"
    page: int
    limit: int


class SaveRouteReq(ClientReq):
    tag: str
    route: List[str]
    other_info: Optional[Dict[str, str]] = None
    type: str = MessageType.SAVE_ROUTE


class UpdateSavedRouteReq(ClientReq):
    tag: str
    other_info: Dict[str, str]


class UpdateSherpaMetaDataReq(ClientReq):
    sherpa_name: str
    info: Dict[str, str]


class ActivateParkingMode(ClientReq):
    activate: bool
    sherpa_name: str
    type: str = MessageType.ACTIVATE_PARKING_MODE


#################################################
# Messages from super_users
class SuperUserReq(BaseModel):
    source: Union[str, None] = None
    type: str
    timestamp: float
    ttl: Optional[int] = None


class SuperUserResourceReq(SuperUserReq):
    visa: VisaReq = None
    # TODO: define types for these
    parking_slot: str = None
    charging_bay: str = None
    access_type: AccessType = None
    ttl = 5
    type = MessageType.RESOURCE_ACCESS


#################################################
# Messages to sherpas
class FMReq(BaseModel):
    source: Union[str, None] = None
    endpoint: str
    ttl: Optional[int] = None
    ack_reqd: Optional[bool] = True


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
    basic_trip_description: Optional[dict]


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
    basic_trip_description: Optional[dict]


class PauseResumeReq(FMReq):
    endpoint: str = PasstoSherpaEndpoints.PAUSE_RESUME
    pause: bool
    sherpa_name: str
    type = MessageType.PASS_TO_SHERPA


class SwitchModeReq(FMReq):
    endpoint: str = PasstoSherpaEndpoints.SWITCH_MODE
    mode: str
    sherpa_name: str
    type = MessageType.PASS_TO_SHERPA


class ResetPoseReq(FMReq):
    endpoint: str = PasstoSherpaEndpoints.RESET_POSE
    pose: List[float]
    sherpa_name: str
    station_name: Optional[str]
    type = MessageType.PASS_TO_SHERPA

class ResetPoseVPRReq(FMReq):
    endpoint: str = PasstoSherpaEndpoints.RESET_POSE_VPR
    sherpa_name: str
    type = MessageType.PASS_TO_SHERPA


class DiagnosticsReq(FMReq):
    endpoint: str = PasstoSherpaEndpoints.DIAGNOSTICS
    sherpa_name: str
    type = MessageType.PASS_TO_SHERPA


class QuickDiagnosticsReq(FMReq):
    endpoint: str = PasstoSherpaEndpoints.QUICK_DIAGNOSTICS
    sherpa_name: str
    type = MessageType.PASS_TO_SHERPA


class RevokeVisaReq(FMReq):
    endpoint: str = PasstoSherpaEndpoints.REVOKE_VISA
    sherpa_name: Optional[str]
    visa_type: str
    zone_name: str
    type = MessageType.PASS_TO_SHERPA

class SoundSettingReq(FMReq):
    endpoint: str = PasstoSherpaEndpoints.SOUND
    sherpa_name: str
    volume: float
    sound_type: str
    type = MessageType.PASS_TO_SHERPA

class CurrentSoundSettingReq(FMReq):
    endpoint: str = PasstoSherpaEndpoints.CURRENT_SOUND_STATUS
    sherpa_name: str
    type = MessageType.PASS_TO_SHERPA


class SherpaImgUpdate(FMReq):
    endpoint: str = PasstoSherpaEndpoints.IMG_UPDATE
    image_tag: str
    fm_server_username: str
    time_zone: str


class ManualVisaReleaseReq(ClientReq):
    revoke_visa_for: str
    zone_id: str
    type = MessageType.MANUAL_VISA_RELEASE

class SoundSettingCtrlReq(ClientReq):
    volume: Optional[float] = 0.01
    sound_type: str

class RemoteTerminalCtrlReq(ClientReq):
    enable_remote_terminal: bool
    code: Optional[str]


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
