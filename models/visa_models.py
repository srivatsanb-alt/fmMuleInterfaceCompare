from sqlalchemy import Boolean, Column, ForeignKey, ForeignKeyConstraint, Integer, String
from sqlalchemy.orm import relationship

from models.base_models import Base, TimestampMixin
from models.fleet_models import Sherpa


class ZoneType:
    STATION = "station"
    LANE = "lane"


class ExclusionZone(Base, TimestampMixin):
    __tablename__ = "exclusion_zones"
    zone_id = Column(String, primary_key=True)
    zone_type = Column(String, primary_key=True)
    sherpas = relationship(
        "Sherpa", secondary="visa_assignments", back_populates="exclusion_zones"
    )
    # Whether this zone is currently locked exclusively by a sherpa. In that case, sherpas can
    # have length at most one.
    exclusivity = Column(Boolean)


class VisaAssignment(Base, TimestampMixin):
    __tablename__ = "visa_assignments"
    zone_id = Column(String, primary_key=True)
    zone_type = Column(String, primary_key=True)
    sherpa_name = Column(String, ForeignKey(Sherpa.name), primary_key=True)
    __table_args__ = (
        ForeignKeyConstraint(
            ["zone_id", "zone_type"],
            ["exclusion_zones.zone_id", "exclusion_zones.zone_type"],
        ),
    )
