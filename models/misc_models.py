from models.base_models import Base, TimestampMixin
from sqlalchemy import Column, Integer, String, ARRAY


class Notifications(TimestampMixin, Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    entity_names = ARRAY(Column(String))
    notification = Column(String)
    module = Column(String)
