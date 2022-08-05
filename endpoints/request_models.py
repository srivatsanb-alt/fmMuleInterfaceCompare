import json
from dataclasses import asdict, dataclass, fields
from enum import Enum
from typing import List, Union

from core.constants import MessageType
from pydantic import BaseModel


# Messages from sherpas to FM
class SherpaReq(BaseModel):
    source: Union[str, None] = None
    type: str


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


# Messages from sherpas to FM (Websocket)
class JsonMixin:
    @classmethod
    def from_dict(cls, obj_dict):
        flds = [f.name for f in fields(cls)]
        attribs = {k: v for (k, v) in obj_dict.items() if k in flds}
        return cls(**attribs)

    @classmethod
    def from_json(cls, obj_json):
        return cls.from_dict(json.loads(obj_json))

    def to_json(self):
        return json.dumps(asdict(self))


@dataclass
class SherpaStatusMsg(JsonMixin):
    type: str
    timestamp: float
    sherpa_name: str
    current_pose: list
    battery_status: float
    mode: str
    error: bool
    error_info: str = None


# Messages from FM to sherpas
class FMReq(BaseModel):
    endpoint: str


class DirectionEnum(str, Enum):
    send = "send"
    receive = "receive"


class MoveReq(FMReq):
    endpoint: str = "move_to"
    trip_id: int
    trip_leg_id: int
    destination_pose: List[float]
    destination_name: str


class HitchReq(BaseModel):
    hitch: bool


class ConveyorReq(BaseModel):
    direction: DirectionEnum
    num_units: int


class DispatchButtonReq(BaseModel):
    value: bool


class PeripheralsReq(FMReq):
    endpoint: str = "peripherals"
    hitch_msg: HitchReq = None
    conv_msg: ConveyorReq = None


class MapFileInfo(BaseModel):
    file_name: str
    hash: str


class InitReq(FMReq):
    endpoint: str = "init"
    fleet_name: str
    map_files: List[MapFileInfo]


@dataclass
class InitResp(JsonMixin):
    display_name: str
    hwid: str
    ip_address: str
    map_files_match: bool
