from models.base_models import Base, TimestampMixin
from sqlalchemy import Column, Integer, String, ARRAY, Boolean


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
    stale_alert_or_action = "stale_alert_or_action"
    action_request = "action_request"
    stale_alert_or_action = "stale_alert_or_action"


NotificationTimeout = {
    NotificationLevels.info: 120,
<<<<<<< HEAD
    NotificationLevels.action_request: 150,
    NotificationLevels.alert: 150,
=======
    NotificationLevels.action_request: 120,
    NotificationLevels.alert: 120,
    NotificationLevels.stale_alert_or_action: 300,
>>>>>>> fm_dev
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
