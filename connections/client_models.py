from sqlalchemy import (
    Column,
    Integer,
    String
)

from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()


class ClientAuth(Base):
    __tablename__ = "client_auth"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    hashed_api_key = Column(String, unique=True, index=True)


# bosch IES psql data
class BoschIESEntities(Base):
    __tablename__ = "bosch_ies_data"
    entity_name = Column(String, unique=True, index=True)
    entity_type = Column(String, unique=True, index=True)
    external_id = Column(String, unique=True, index=True)
    map = Column(String)


class BoschIESTrips(Base):
    __tablename__ = "bosch_ies_trips"
    id = Column(Integer, primary_key=True, index=True)
    trid_id = Column(String, unique=True, index=True)
    external_id = Column(String, unique=True, index=True)
