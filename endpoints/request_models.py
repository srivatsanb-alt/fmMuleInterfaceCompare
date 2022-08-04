from enum import Enum
from typing import List, Union
from pydantic import BaseModel

from core.constants import MessageType

# Messages from sherpas to FM


class SherpaMsg(BaseModel):
    source: Union[str, None] = None
    type: str


class InitExtraInfo(BaseModel):
    display_name: str
    ip_address: str
    chassis_number: str


class InitMsg(SherpaMsg):
    current_pose: List[float]
    extra_info: Union[InitExtraInfo, None] = None
    type = MessageType.INIT


class ReachedMsg(SherpaMsg):
    trip_id: int
    trip_leg_id: int
    destination_pose: List[float]
    destination_name: str
    type = MessageType.REACHED


# Messages from FM to sherpas
class FMCommand(BaseModel):
    endpoint: str


class DirectionEnum(str, Enum):
    send = "send"
    receive = "receive"


class MoveMsg(FMCommand):
    endpoint: str = "move_to"
    trip_id: int
    trip_leg_id: int
    destination_pose: List[float]
    destination_name: str


class HitchMsg(BaseModel):
    hitch: bool


class ConveyorMsg(BaseModel):
    direction: DirectionEnum
    num_units: int


class DispatchButtonMsg(BaseModel):
    value: bool


class PeripheralsMsg(FMCommand):
    endpoint: str = "peripherals"
    hitch_msg: HitchMsg = None
    conv_msg: ConveyorMsg = None
