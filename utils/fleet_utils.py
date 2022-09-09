import hashlib
import os
import secrets
from core.db import engine
import json
import glob
import sys
import importlib

from models.fleet_models import (
    Fleet,
    Map,
    MapFile,
    Sherpa,
    SherpaStatus,
    Station,
    StationStatus,
)

from models.base_models import (
    StationProperties
)

from core.db import session_maker
from sqlalchemy.exc import NoResultFound


def gen_api_key(hwid):
    return secrets.token_urlsafe(32) + "_" + hwid


def add_sherpa(sherpa_name: str, hwid=None, ip_address=None, api_key=None, fleet_id=None):
    if not hwid:
        raise ValueError("Sherpa hardware id cannot be null")
    if not api_key:
        api_key = gen_api_key(hwid)
    hashed_api_key = hashlib.sha256(api_key.encode("utf-8")).hexdigest()
    with session_maker() as db:
        sherpa = Sherpa(
            name=sherpa_name,
            hwid=hwid,
            ip_address=ip_address,
            hashed_api_key=hashed_api_key,
            fleet_id=fleet_id,
        )
        sherpa_status = SherpaStatus(sherpa_name=sherpa_name)
        db.add(sherpa)
        db.add(sherpa_status)
        db.commit()

    return api_key


def add_update_fleet(**kwargs):
    fleet_name = kwargs.get("name")
    if not fleet_name:
        raise ValueError("fleet name should not be null")
    with session_maker() as db:
        try:
            fleet: Fleet = db.query(Fleet).filter(Fleet.name == fleet_name).one()
        except NoResultFound:
            fleet = Fleet()
            db.add(fleet)
        for col in Fleet.__table__.columns.keys():
            val = kwargs.get(col)
            if not val:
                continue
            setattr(fleet, col, val)
        db.commit()

    return fleet


def add_sherpa_to_fleet(sherpa: str, fleet: str):
    if not fleet or not sherpa:
        raise ValueError("Fleet and sherpa names cannot be null")
    with session_maker() as db:
        db_fleet: Fleet = db.query(Fleet).filter(Fleet.name == fleet).one()
        db_sherpa: Sherpa = db.query(Sherpa).filter(Sherpa.name == sherpa).one()
        db_sherpa.fleet_id = db_fleet.id
        db.commit()


def add_update_station(**kwargs):
    station_name = kwargs.get("name")
    properties = kwargs.get("properties")
    if not station_name:
        raise ValueError("station name should not be null")
    with session_maker() as db:
        try:
            station: Station = db.query(Station).filter_by(name=station_name).one()
        except NoResultFound:
            station = Station(properties=properties)
            db.add(station)
            station_status = StationStatus(
                station_name=station_name, disabled=False, arriving_sherpas=[]
            )
            db.add(station_status)
        for col in Station.__table__.columns.keys():
            val = kwargs.get(col)
            if not val:
                continue
            setattr(station, col, val)
        db.commit()


def add_map(fleet: str):
    with session_maker() as db:
        map: Map = Map(name=fleet)
        db.add(map)
        db.flush()
        db.refresh(map)
        fleet_obj: Fleet = db.query(Fleet).filter(Fleet.name == fleet).one()
        fleet_id = fleet_obj.id
        fleet_obj.map_id = map.id
        db.commit()

    add_map_files(fleet)
    grid_map_attributes_path = os.path.join(f"{os.environ['FM_MAP_DIR']}", f"{fleet}", "map", "grid_map_attributes.json")
    if not os.path.exists(grid_map_attributes_path):
        return
    with open(grid_map_attributes_path) as f:
        gmas =json.load(f)
        stations_info = gmas["stations_info"]
        for _, station_info in stations_info.items():
            properties = []
            for tag in station_info["station_tags"]:
                try:
                    properties.append(getattr(StationProperties, tag.upper()))
                except Exception as e:
                    print(f"unable to add station properties, {e}")
                    pass
            add_update_station(
                        name=station_info["station_name"],
                        pose=station_info["pose"],
                        fleet_id=fleet_id,
                        properties=properties
                        )



def add_map_files(fleet_name: str):
    path_prefix = os.path.join(os.environ['FM_MAP_DIR'], f"{fleet_name}/map")
    with open(f"{path_prefix}/map_files.txt") as f:
        map_files = f.readlines()

    with session_maker() as db:
        fleet: Fleet = db.query(Fleet).filter(Fleet.name == fleet_name).one()
        map_id = fleet.map_id
        for map_file_name in map_files:
            map_file_name = map_file_name.rstrip()
            map_file_path = f"{path_prefix}/{map_file_name}"
            sha1 = compute_sha1_hash(map_file_path)
            map_file = MapFile(map_id=map_id, filename=map_file_name, file_hash=sha1)
            db.add(map_file)
        db.commit()


def create_all_tables(drop=False):
    all_files = glob.glob("models/*.py")
    for file in all_files:
        module = file.split('.')[0]
        module = module.replace("/",".")
        print(f"looking for models in module: {module}")
        try:
            models = importlib.import_module(module)
            models.Base.metadata.create_all(bind=engine)
            print(f"created tables from {module}")
        except Exception as e:
            print(f"failed to create tables from {module}, {e}")


def create_table(model, drop=False):
    if drop:
        model.__table__.drop(engine)
    model.__table__.metadata(bind=engine)


BUF_SIZE = 65536


def compute_sha1_hash(fpath):
    sha1 = hashlib.sha1()
    with open(fpath, "rb") as f:
        while True:
            data = f.read(BUF_SIZE)
            if not data:
                break
            sha1.update(data)
    return sha1.hexdigest()
