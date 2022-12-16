from sqlalchemy import Integer, String, Column, ARRAY, Float, Boolean
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
import os
import json
from models.base_models import Base
from plugins.plugin_comms import send_req_to_FM
import logging
import hashlib

logger_name = "plugin_conveyor"


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
    hashed_api_key = Column(String, unique=True)
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
        for api_key, conveyor_details in api_key_conveyor_mapping.items():
            conveyor_name = conveyor_details["name"]
            status_code, response_json = send_req_to_FM(
                "plugin_conveyor",
                "station_info",
                req_type="get",
                query=conveyor_name,
            )

            if response_json is not None:
                station_info = response_json
                # if StationProperties.CONVEYOR in station_info["properties"]:
                logging.getLogger(logger_name).info(f"Will add {conveyor_name} to DB")
                station_type = "conveyor"
                hashed_api_key = hashlib.sha256(api_key.encode("utf-8")).hexdigest()
                conv_info = ConvInfo(
                    name=conveyor_details["name"],
                    hashed_api_key=hashed_api_key,
                    num_totes=0,
                    type=station_type,
                    nearest_chute=conveyor_details["nearest_chute"],
                    fleet_name=station_info["fleet_name"],
                    pose=station_info["pose"],
                    disabled=station_info["disabled"],
                )
                db.add(conv_info)
            db.commit()
