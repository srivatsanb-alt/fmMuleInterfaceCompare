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
from sqlalchemy.orm import relationship
from models.base_models import Base
from models.visa_models import VisaAssignment


class SuperUser(Base):
    __tablename__ = "super_users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    hashed_api_key = Column(String, unique=True, index=True)
    description = Column(String)

    exclusion_zones = relationship(
        "ExclusionZone", secondary=VisaAssignment.__table__, back_populates="super_users"
    )

    def get_notification_entity_names(self):
        entity_names = [self.name]    
        return entity_names

    