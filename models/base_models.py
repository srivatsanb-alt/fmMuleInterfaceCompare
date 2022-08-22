import dataclasses
import enum
import json
from sqlalchemy import Column, DateTime, func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class JsonMixin:
    @classmethod
    def from_dict(cls, obj_dict):
        fields = [f.name for f in dataclasses.fields(cls)]
        attribs = {k: v for (k, v) in obj_dict.items() if k in fields}
        return cls(**attribs)

    @classmethod
    def from_json(cls, obj_json):
        return cls.from_dict(json.loads(obj_json))

    def to_json(self):
        return json.dumps(dataclasses.asdict(self))


class TimestampMixin(object):
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    created_at._creation_order = 9998
    updated_at._creation_order = 9998


class StationProperties(enum.Enum):
    PARKING = 1
    PICKUP = 2
    DROP = 3
    AUTO_HITCH = 4
    AUTO_UNHITCH = 5
    DISPATCH_NOT_REQD = 6
    CHARGING = 7
