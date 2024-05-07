from sqlalchemy import Boolean, Column, ForeignKey, String, ARRAY, Integer
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
    waiting_super_users = relationship("SuperUser", secondary="visa_rejects")
    sherpas = relationship(
        "Sherpa", secondary="visa_assignments", back_populates="exclusion_zones"
    )
    super_users = relationship(
        "SuperUser", secondary="visa_assignments", back_populates="exclusion_zones"
    )
    prev_linked_gates = relationship(
        "ExclusionZone",
        secondary="linked_gates",
        backref="next_linked_gates",
        primaryjoin="ExclusionZone.zone_id==LinkedGates.prev_zone_id",
        secondaryjoin="ExclusionZone.zone_id==LinkedGates.next_zone_id",
    )
    exclusivity = Column(Boolean)
    fleets = Column(ARRAY(String))

    def access_held_by(self):
        access_held_by = [s.name for s in self.sherpas] + [s.name for s in self.super_users]
        return access_held_by

    def provide_access(self, requester):
        if requester.__tablename__ == "super_users":
            self.super_users.append(requester)
            if requester in self.waiting_super_users:
                self.waiting_super_users.remove(requester)
        else:
            self.sherpas.append(requester)
            if requester in self.waiting_sherpas:
                self.waiting_sherpas.remove(requester)
        

    def revoke_access(self, requester):
        if requester.__tablename__ == "super_users":
            if requester in self.super_users:
                self.super_users.remove(requester)
        else:
            if requester in self.sherpas:
                self.sherpas.remove(requester)
            

class VisaAssignment(Base, TimestampMixin):
    __tablename__ = "visa_assignments"
    id = Column(Integer, primary_key=True)
    zone_id = Column(String, ForeignKey("exclusion_zones.zone_id")) # zone_id = {zone_name}_{zone_type}
    sherpa_name = Column(String, ForeignKey("sherpas.name"), nullable=True)
    user_name = Column(String, ForeignKey("super_users.name"), nullable=True)

class VisaRejects(Base, TimestampMixin):
    __tablename__ = "visa_rejects"
    id = Column(Integer, primary_key=True)
    zone_id = Column(String, ForeignKey("exclusion_zones.zone_id"))
    sherpa_name = Column(String, ForeignKey("sherpas.name"), nullable=True)
    user_name = Column(String, ForeignKey("super_users.name"), nullable=True)
    reason = Column(String)
