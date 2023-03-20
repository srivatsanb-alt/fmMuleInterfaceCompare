import os
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine
from sqlalchemy import Integer, String, Column, ARRAY, Boolean
from dataclasses import dataclass
from models.base_models import Base, JsonMixin
from pydantic import BaseModel
from typing import Union, Optional


class DBSession:
    def __init__(self):
        engine = create_engine(
            os.path.join(os.getenv("FM_DATABASE_URI"), "plugin_conveyor")
        )
        session_maker = sessionmaker(autocommit=False, autoflush=True, bind=engine)
        self.session: Session = session_maker()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type or exc_value or traceback:
            self.close(commit=False)
        else:
            self.close()

    def close(self, commit=True):
        if commit:
            self.session.commit()
        self.session.close()


class ConvTrips(Base):
    __tablename__ = "conveyor_trips"
    __table_args__ = {"extend_existing": True}
    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer)
    route = Column(ARRAY(String))
    trip_id = Column(String, unique=True)
    active = Column(Boolean, index=True)


class ConvInfo(Base):
    __tablename__ = "conveyor_info"
    __table_args__ = {"extend_existing": True}
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    hashed_api_key = Column(String, unique=True)
    num_totes = Column(Integer)
    nearest_chute = Column(String)
    fleet_name = Column(String)


@dataclass
class ToteStatus(JsonMixin):
    num_totes: int
    compact_time: int
    type: str
    name: str = None


class ClientReq(BaseModel):
    source: Union[str, None] = None


class AddEditConvReq(ClientReq):
    station_name: str
    nearest_chute: str
    api_key: Optional[str]
