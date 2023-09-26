from models.base_models import Base, TimestampMixin
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Column, Integer, String, ARRAY, Boolean, DateTime

# FM incident types
FMIncidentTypes = ["mule_error", "fm_error"]
ConditionalTripTags = ["exclude_stations", "battery_swap", "parking"]


class NotificationModules:
    generic = "generic"
    errors = "errors"
    trip = "trip"
    visa = "visa"
    conveyor = "conveyor"
    trolley = "trolley"
    stoppages = "stoppages"
    dispatch_button = "dispatch_button"


class NotificationLevels:
    info = "info"
    alert = "alert"
    stale_alert_or_action = "stale_alert_or_action"
    action_request = "action_request"


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

    # incident code
    code = Column(String, nullable=False)

    # sherpa name, module name
    entity_name = Column(String)

    # unqiue incident id
    incident_id = Column(String, unique=True, index=True)

    # data details
    data_uploaded = Column(Boolean)
    data_path = Column(String)

    # extra info
    module = Column(String)
    sub_module = Column(String)
    message = Column(String, nullable=False)
    display_message = Column(String)
    recovery_message = Column(String)
    other_info = Column(JSONB)


class SherpaModeChange(Base):
    __tablename__ = "sherpa_mode_change"
    id = Column(Integer, primary_key=True)
    sherpa_name = Column(String, nullable=False, index=True)
    mode = Column(String, nullable=False, index=True)
    started_at = Column(DateTime, index=True, nullable=False)
    ended_at = Column(DateTime, index=True)


class SherpaOEE(Base):
    __tablename__ = "sherpa_oee"
    id = Column(Integer, primary_key=True)
    sherpa_name = Column(String, nullable=False, index=True)
    dt = Column(DateTime, nullable=False, index=True)
    mode_split_up = Column(JSONB)


class FileUploads(Base, TimestampMixin):
    __tablename__ = "file_uploads"
    filename = Column(String, primary_key=True)
    type = Column(String, index=True)
    path = Column(String, index=True)
    uploaded_by = Column(String, nullable=False, index=True)
    fm_incident_id = Column(String, index=True)
    other_info = Column(JSONB)
