from models.base_models import Base, TimestampMixin
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Column, Integer, String, ARRAY, Boolean
from typing import Optional


class NotificationModules:
    generic = "generic"
    trip = "trip"
    visa = "visa"
    obstructed = "obstructed"
    peripheral_devices = "peripheral_devices"
    map_file_check = "map_file_check"
    dispatch_button = "dispatch_button"


class NotificationLevels:
    info = "info"
    alert = "alert"
    action_request = "action_request"
    stale_alert_or_action = "stale_alert_or_action"


class FMIncidentTypes:
    mule_error = "mule_error"
    fm_error = "fm_error"


NotificationTimeout = {
    NotificationLevels.info: 120,
    NotificationLevels.action_request: 120,
    NotificationLevels.alert: 120,
    NotificationLevels.stale_alert_or_action: 300,
}


class Notifications(TimestampMixin, Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    entity_names = Column(ARRAY(String))
    log = Column(String)
    log_level = Column(String, index=True)
    module = Column(String)
    cleared_by = Column(ARRAY(String))
    repetitive = Column(Boolean)
    repetition_freq = Column(Integer)


class FMVersion(Base):
    __tablename__ = "fm_version"
    version = Column(String, primary_key=True)


class SoftwareCompatability(Base):
    __tablename__ = "software_compatability"
    id = Column(Integer, primary_key=True)
    info = Column(JSONB)


class MasterFMDataUpload(Base):
    __tablename__ = "master_fm_data_upload"
    id = Column(Integer, primary_key=True)
    info = Column(JSONB)


class FMIncidents(TimestampMixin, Base):
    __tablename__ = "fm_incidents"
    id = Column(Integer, primary_key=True)
    type = Column(String, nullable=False)
    error_code = Column(String, nullable=False)
    entity_name = Column(String)
    module = Column(String)
    sub_module = Column(String)
    error_message = Column(String, nullable=False)
    display_message = Column(String)
    recovery_message = Column(String)
    other_info = Column(JSONB)
