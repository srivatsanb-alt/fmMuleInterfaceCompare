from typing import List, Union
from pydantic import BaseModel

from core.constants import MessageType


class InitExtraInfo(BaseModel):
    display_name: str
    ip_address: str
    chassis_number: str


class InitMsg(BaseModel):
    current_pose: List[float]
    source: Union[str, None] = None
    extra_info: Union[InitExtraInfo, None] = None
    type = MessageType.INIT
