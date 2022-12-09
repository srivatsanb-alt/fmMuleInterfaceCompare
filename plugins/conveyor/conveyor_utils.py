from sqlalchemy import Integer, String, Column, ARRAY, Float, Boolean
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
import os
import json
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class ConvTrips(Base):
    __tablename__ = "conveyor_trips"
    __table_args__ = {"extend_existing": True}
    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer)
    route = Column(ARRAY(String))
    trip_id = Column(String, unique=True)
    trip_metadata = Column(JSONB)


class ConvInfo(Base):
    __tablename__ = "conveyor_info"
    __table_args__ = {"extend_existing": True}
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    api_key = Column(String, unique=True)
    type = Column(String)
    pose = Column(ARRAY(Float))
    num_totes = Column(Integer)
    disabled = Column(Boolean)
    nearest_chute = Column(String)
    fleet_name = Column(String)


engine = create_engine(os.path.join(os.getenv("FM_DATABASE_URI"), "plugin_conveyor"))
session_maker = sessionmaker(autocommit=False, autoflush=True, bind=engine)
session = session_maker()


def populate_conv_info():
    with session as db:
        api_key_conveyor_mapper = os.path.join(
            os.getenv("FM_MAP_DIR"), "plugin_conveyor", "api_key_conveyor_mapping.json"
        )
        with open(api_key_conveyor_mapper, "r") as f:
            api_key_conveyor_mapping = json.load(f)
        for api, conveyor in api_key_conveyor_mapping.items():
            info = ConvInfo(
                name=conveyor["name"],
                api_key=api,
                num_totes=0,
                nearest_chute=conveyor["nearest_chute"],
                fleet_name="all_hands_map",
                pose=conveyor["pose"],
            )
            db.add(info)
        db.commit()
