from sqlalchemy import (
    ARRAY,
    Boolean,
    Column,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    DateTime,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from models.base_models import Base, StationProperties, TimestampMixin
from models.visa_models import VisaAssignment
from sqlalchemy import Integer, ForeignKey

class FleetsMaster(Base, TimestampMixin):
    __tablename__ = "fleets_master"
    fleet_id = Column(Integer, primary_key=True, autoincrement=True)
    fleet_name = Column(String(100), nullable=False, index=True, unique=True)
    fm_fleet_id = Column(Integer, nullable=True)

class UserFleet(Base, TimestampMixin):
    __tablename__ = "users_fleets"

    user_fleet_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    fleet_id = Column(Integer, ForeignKey("fleets_master.fleet_id"), nullable=False)

class User(Base, TimestampMixin):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    user_name = Column(String(120), nullable=False, unique=True)
    user_email = Column(String(120), nullable=False, unique=True)