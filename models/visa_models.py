from sqlalchemy import Boolean, Column, ForeignKey, String, ARRAY
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
    waiting_sherpas = relationship("Sherpa", secondary="visa_rejects")
    sherpas = relationship(
        "Sherpa", secondary="visa_assignments", back_populates="exclusion_zones"
    )
    foreign_bots = relationship(
        "ForeignBot", secondary="foreign_visa_assignments", back_populates="exclusion_zones")
    prev_linked_gates = relationship(
        "ExclusionZone",
        secondary="linked_gates",
        backref="next_linked_gates",
        primaryjoin="ExclusionZone.zone_id==LinkedGates.prev_zone_id",
        secondaryjoin="ExclusionZone.zone_id==LinkedGates.next_zone_id",
    )
    exclusivity = Column(Boolean)
    fleets = Column(ARRAY(String))


class VisaAssignment(Base, TimestampMixin):
    __tablename__ = "visa_assignments"
    zone_id = Column(String, ForeignKey("exclusion_zones.zone_id"), primary_key=True)
    sherpa_name = Column(String, ForeignKey("sherpas.name"), primary_key=True)


class VisaRejects(Base, TimestampMixin):
    __tablename__ = "visa_rejects"
    zone_id = Column(String, ForeignKey("exclusion_zones.zone_id"), primary_key=True)
    sherpa_name = Column(String, ForeignKey("sherpas.name"), primary_key=True)
    reason = Column(String)


class ForeignVisaRejects(Base, TimestampMixin):
    __tablename__ = "foreign_visa_rejects"
    zone_id = Column(String, ForeignKey("exclusion_zones.zone_id"), primary_key=True)
    bot_name = Column(String, ForeignKey("foreign_bots.name"), primary_key=True)
    reason = Column(String)


class ForeignVisaAssignment(Base, TimestampMixin):
    __tablename__ = "foreign_visa_assignments"
    zone_id = Column(String, ForeignKey("exclusion_zones.zone_id"), primary_key=True)
    bot_name = Column(String, ForeignKey("foreign_bots.name"), primary_key=True)
