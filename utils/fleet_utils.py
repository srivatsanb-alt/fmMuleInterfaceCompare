import hashlib
import secrets


from models.fleet_models import Fleet, Sherpa, SherpaStatus, Station, StationStatus
from core.db import session_maker


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


def add_fleet(fleet: str, customer=None, site=None, location=None):
    if not fleet:
        raise ValueError("Fleet name cannot be null")
    with session_maker() as db:
        fleet = Fleet(name=fleet, customer=customer, site=site, location=location)
        db.add(fleet)
        db.commit()


def add_sherpa_to_fleet(sherpa: str, fleet: str):
    if not fleet or not sherpa:
        raise ValueError("Fleet and sherpa names cannot be null")
    with session_maker() as db:
        db_fleet: Fleet = db.query(Fleet).filter(Fleet.name == fleet).one()
        db_sherpa: Sherpa = db.query(Sherpa).filter(Sherpa.name == sherpa).one()
        db_sherpa.fleet_id = db_fleet.id
        db.commit()


def add_station(name: str, pose, properties=None, button_id=None):
    with session_maker() as db:
        properties = properties if properties else []
        station: Station = Station(
            name=name, pose=pose, properties=properties, button_id=button_id
        )
        station_status = StationStatus(
            station_name=name, disabled=False, arriving_sherpas=[]
        )
        db.add(station)
        db.add(station_status)
        db.commit()
