import hashlib
import os
import secrets


from models.fleet_models import (
    Fleet,
    Map,
    MapFile,
    Sherpa,
    SherpaStatus,
    Station,
    StationStatus,
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
    if not station_name:
        raise ValueError("station name should not be null")
    with session_maker() as db:
        try:
            station: Station = db.query(Station).filter_by(name=station_name).one()
        except NoResultFound:
            station = Station(properties=[])
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


def add_map(name: str, fleet: str):
    with session_maker() as db:
        map: Map = Map(name=name)
        db.add(map)
        db.commit()
        db.refresh(map)
    add_map_files(fleet)
    add_update_fleet(name=fleet, map_id=map.id)


def add_map_files(fleet_name: str):
    path_prefix = f"{os.environ['FM_MAP_DIR']}/{fleet_name}/map"
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
