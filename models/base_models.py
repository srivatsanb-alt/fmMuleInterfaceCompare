import enum
from sqlalchemy import Column, DateTime, func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


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
    CHARGING = 6
