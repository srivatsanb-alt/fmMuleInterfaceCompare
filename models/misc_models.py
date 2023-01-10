from models.base_models import Base, TimestampMixin
from sqlalchemy import Column, Integer, String, ARRAY


class NotificationModules:
    generic = "generic"
    trip = "trip"
    visa = "visa"
    obstructed = "obstructed"
    peripheral_devices = "peripheral_devices"


class NotificationLevels:
    info = "info"
    alert = "alert"
    action_request = "action_request"


NotificationTimeout = {
    NotificationLevels.info: 120,
    NotificationLevels.action_request: 300,
    NotificationLevels.alert: 300,
}


class Notifications(TimestampMixin, Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    entity_names = Column(ARRAY(String))
    log = Column(String)
    log_level = Column(String, index=True)
    module = Column(String)
    cleared_by = Column(ARRAY(String))


class FMVersion(Base):
    __tablename__ = "fm_version"
    version = Column(String, primary_key=True)
