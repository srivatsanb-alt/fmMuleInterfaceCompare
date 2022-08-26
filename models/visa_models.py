from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from models.base_models import Base, TimestampMixin


class ZoneType:
    STATION = "station"
    LANE = "lane"


class LinkedGates(Base, TimestampMixin):
    __tablename__ = "linked_gates"
    prev_zone_id = Column(String, ForeignKey("exclusion_zones.zone_id"), primary_key=True)
    next_zone_id = Column(String, ForeignKey("exclusion_zones.zone_id"), primary_key=True)


class ExclusionZone(Base, TimestampMixin):
    __tablename__ = "exclusion_zones"
    zone_id = Column(String, primary_key=True, unique=True)
    sherpas = relationship(
        "Sherpa", secondary="visa_assignments", back_populates="exclusion_zones"
    )
    prev_linked_gates = relationship(
        "ExclusionZone",
        secondary="linked_gates",
        backref="next_linked_gates",
        primaryjoin="ExclusionZone.zone_id==LinkedGates.prev_zone_id",
        secondaryjoin="ExclusionZone.zone_id==LinkedGates.next_zone_id",
    )
    # Whether this zone is currently locked exclusively by a sherpa. In that case, sherpas can
    # have length at most one.
    exclusivity = Column(Boolean)


class VisaAssignment(Base, TimestampMixin):
    __tablename__ = "visa_assignments"
    zone_id = Column(String, ForeignKey("exclusion_zones.zone_id"), primary_key=True)
    sherpa_name = Column(String, ForeignKey("sherpas.name"), primary_key=True)
