from models.base_models import Base
from sqlalchemy import Column, String, Integer, Boolean


class ExternalConnections(Base):
    __tablename__ = "external_connections"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    fleet_name = Column(String)
    hashed_password = Column(String)
    status = Column(Boolean)
