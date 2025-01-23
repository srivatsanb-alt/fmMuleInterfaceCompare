from sqlalchemy import ARRAY, Column, DateTime, ForeignKey, Integer, String, Boolean, Float, BIGINT
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

#ati code imports
from models.base import Base, TimestampMixin


    
class SherpaHealth(Base):
    __tablename__ = "sherpa_health"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    sherpa_name = Column(String, index=True)
    sw_tag_id = Column(Integer, ForeignKey("sw_history.id"), index=True)
    start_time = Column(DateTime, index=True)
    end_time = Column(DateTime, index=True)
    display_name = Column(String, index=True)
    hardware_id = Column(String, index=True)
    total_lidar_frames = Column(Integer, index=True)
    missing_lidar_frames = Column(Integer, index=True)
    total_encoder_exceptions = Column(ARRAY(Integer), index=True)
    disk_usage = Column(Float, index=True)
    max_cpu_temperature = Column(Float, index=True)
    max_cpu_load = Column(Float, index=True)
    max_wifi_temperature = Column(Float, index=True)
    max_memory_used = Column(Float, index=True)
    max_drivable_processing_time = Column(Float, index=True)
    max_yelli_processing_time = Column(Float, index=True)
    total_distance = Column(Float, index=True)
    RX_packets = Column(Float, index=True)
    TX_packets = Column(Float, index=True)
    total_runs = Column(Integer, index=True)
    total_usb_resets = Column(Integer, index=True)
    total_reboots = Column(Integer, index=True)
    meta_data = Column(JSONB)



class SherpaRuns(Base):
    __tablename__ = "sherpa_runs"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    start_time = Column(DateTime, index=True)
    end_time = Column(DateTime, index=True)
    sw_tag_id = Column(Integer, ForeignKey("sw_history.id"), index=True)
    total_lidar_frames = Column(Integer, index=True)
    missing_lidar_sectors = Column(Float, index=True)
    encoder_exceptions = Column(ARRAY(Integer), index=True)
    distance = Column(Float, index=True)
    error = Column(String, index=True, nullable=True)
    battery = Column(ARRAY(Float), index=True)
    meta_data = Column(JSONB)

class sw_history(Base, TimestampMixin):
    __tablename__ = "sw_history"
    id = Column(Integer(), primary_key=True, autoincrement=True, index=True)
    version = Column(String(100), index=True)
    date = Column(DateTime(), index=True)
    sw_tag_id = Column(Integer(), ForeignKey("sw_tags.id"), index=True)

