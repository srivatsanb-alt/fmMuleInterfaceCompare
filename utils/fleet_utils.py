import hashlib
import os
import sys
import secrets
import logging
from core.db import engine
from core.db import session_maker
import json
import glob
import importlib
import inspect
from sqlalchemy.exc import NoResultFound
from sqlalchemy import inspect as sql_inspect
from sqlalchemy.sql import not_
from utils.util import dt_to_str
from models.fleet_models import (
    Fleet,
    Map,
    MapFile,
    Sherpa,
    SherpaStatus,
    Station,
    StationStatus,
    AvailableSherpas,
    OptimalDispatchState,
)
import datetime
from models.visa_models import ExclusionZone, LinkedGates
from models.frontend_models import FrontendUser
from models.base_models import StationProperties

logging.getLogger().level == logging.ERROR
sys.path.append(os.environ["MULE_ROOT"])
import mule.ati.tools.gmaj_creator as gmac
import mule.ati.control.bridge.router_planner_interface as rpi
import mule.ati.control.dynamic_router.graph_builder_utils as gbu


def get_table_as_dict(model, model_obj):
    all_valid_types = ["str", "dict", "list", "int", "float", "bool"]
    cols = [(c.name, c.type.python_type.__name__) for c in model.__table__.columns]
    result = {}
    model_dict = model_obj.__dict__
    for col, col_type in cols:
        if isinstance(model_dict[col], datetime.datetime):
            result.update({col: dt_to_str(model_dict[col])})
        elif inspect.isclass(model_dict[col]):
            pass
        elif col_type not in all_valid_types:
            pass
        else:
            if isinstance(model_dict[col], list):
                skip = False
                for item in model_dict[col]:
                    if type(item).__name__ not in all_valid_types:
                        skip = True
                        break
                if skip:
                    continue
            result.update({col: model_dict[col]})
    return result


def gen_api_key(hwid):
    return secrets.token_urlsafe(32) + "_" + hwid


def add_sherpa(sherpa_name: str, hwid=None, ip_address=None, api_key=None, fleet_name=None):
    if not hwid:
        raise ValueError("Sherpa hardware id cannot be null")
    if not api_key:
        api_key = gen_api_key(hwid)
    hashed_api_key = hashlib.sha256(api_key.encode("utf-8")).hexdigest()
    with session_maker() as db:
        try:
            sherpa: Sherpa = db.query(Sherpa).filter(Sherpa.name == sherpa_name).one()
        except NoResultFound:
            sherpa = Sherpa(
                name=sherpa_name,
                hwid=hwid,
                ip_address=ip_address,
                hashed_api_key=hashed_api_key,
                fleet_id=1,
            )
            print(f"Added sherpa: {sherpa.__dict__}")
            sherpa_status = SherpaStatus(sherpa_name=sherpa_name, other_info={})
            db.add(sherpa)
            db.add(sherpa_status)
            db.commit()

            add_sherpa_to_fleet(sherpa=sherpa_name, fleet=fleet_name)
            add_sherpa_availability(sherpa_name, fleet_name, False)
    return api_key


def add_sherpa_availability(sherpa_name: str, fleet_name: str, available):
    with session_maker() as db:
        try:
            sherpa_availability: AvailableSherpas = (
                db.query(AvailableSherpas)
                .filter(AvailableSherpas.sherpa_name == sherpa_name)
                .one()
            )
        except NoResultFound:
            sherpa_availability = AvailableSherpas(
                sherpa_name=sherpa_name,
                fleet_name=fleet_name,
                available=available,
            )
            db.add(sherpa_availability)
            db.commit()


def add_fleet(**kwargs):
    fleet_name = kwargs.get("name")
    if not fleet_name:
        raise ValueError("fleet name should not be null")
    with session_maker() as db:
        try:
            fleet: Fleet = db.query(Fleet).filter(Fleet.name == fleet_name).one()
        except NoResultFound:
            fleet = Fleet()
            db.add(fleet)
            optimal_dispatch_state = OptimalDispatchState(
                fleet_name=fleet_name, last_assignment_time=datetime.datetime.now()
            )
            db.add(optimal_dispatch_state)
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


def add_update_station(dbsession, station_info, fleet_id):
    properties = []
    for tag in station_info["station_tags"]:
        try:
            properties.append(getattr(StationProperties, tag.upper()))
        except Exception as e:
            print(f"unable to add station properties, {e}")
            pass

    station_name = station_info["station_name"]
    station_pose = station_info["pose"]
    station: Station = dbsession.query(Station).filter_by(name=station_name).one_or_none()
    if station is None:
        station = Station(
            name=station_name,
            pose=station_pose,
            properties=properties,
            fleet_id=fleet_id,
        )
        dbsession.add(station)
        station_status = StationStatus(
            station_name=station_name, disabled=False, arriving_sherpas=[]
        )
        dbsession.add(station_status)
    else:
        station.pose = station_info["pose"]
        station.properties = properties


def add_update_map_files(dbsession, fleet_name):
    fleet_path = os.path.join(os.environ["FM_MAP_DIR"], f"{fleet_name}/map")
    map_files = get_filenames(fleet_path)
    fleet: Fleet = dbsession.query(Fleet).filter(Fleet.name == fleet_name).one()
    map_id = fleet.map_id
    for map_file_name in map_files:
        map_file_name = map_file_name.rstrip()
        map_file_path = f"{fleet_path}/{map_file_name}"
        sha1 = compute_sha1_hash(map_file_path)
        try:
            map_file: MapFile = (
                dbsession.query(MapFile)
                .filter_by(map_id=map_id)
                .filter_by(filename=map_file_name)
                .one()
            )
            map_file.file_hash = sha1
        except NoResultFound:
            map_file = MapFile(map_id=map_id, filename=map_file_name, file_hash=sha1)
            dbsession.add(map_file)
            dbsession.flush()
            dbsession.refresh(map_file)


def add_map(fleet: str):
    with session_maker() as db:
        try:
            map: Map = db.query(Map).filter_by(name=fleet).one()
        except NoResultFound:
            map: Map = Map(name=fleet)
            db.add(map)
            db.flush()
            db.refresh(map)
            fleet_obj: Fleet = db.query(Fleet).filter(Fleet.name == fleet).one()
            fleet_id = fleet_obj.id
            fleet_obj.map_id = map.id
            db.commit()

            add_update_map_files(db, fleet)
            db.commit()

            grid_map_attributes_path = os.path.join(
                f"{os.environ['FM_MAP_DIR']}", f"{fleet}", "map", "grid_map_attributes.json"
            )
            if not os.path.exists(grid_map_attributes_path):
                return
            with open(grid_map_attributes_path) as f:
                gmas = json.load(f)
                stations_info = gmas["stations_info"]
                for _, station_info in stations_info.items():
                    add_update_station(db, station_info, fleet_id)
                    db.commit()

            add_exclusion_zones(db, fleet)
            db.commit()

            add_linked_gates_table(db, fleet)
            db.commit()


def add_exclusion_zones(dbsession, fleet):
    ez_path = os.path.join(f"{os.environ['FM_MAP_DIR']}", f"{fleet}", "map", "ez.json")
    if not os.path.exists(ez_path):
        return
    with open(ez_path, "r") as f:
        ez_gates = json.load(f)
    for gate in ez_gates["ez_gates"].values():
        gate_name = gate["name"]
        lane_zone_id = f"{gate_name}_lane"
        station_zone_id = f"{gate_name}_station"
        exclusivity = gate["exclusive_parking"]
        try:
            ezone_lane: ExclusionZone = (
                dbsession.query(ExclusionZone).filter_by(zone_id=lane_zone_id).one()
            )
            print(f"EZ gate {lane_zone_id} exists!")
        except Exception as E:
            print(f"{E} Adding new EZ gate {lane_zone_id}")
            ezone_lane = ExclusionZone(zone_id=lane_zone_id)
            dbsession.add(ezone_lane)
            dbsession.flush()
            dbsession.refresh(ezone_lane)
        try:
            ezone_station: ExclusionZone = (
                dbsession.query(ExclusionZone).filter_by(zone_id=station_zone_id).one()
            )
            print(f"EZ gate {station_zone_id} exists!")
        except Exception as E:
            print(f"{E} Adding new EZ gate {station_zone_id}")
            ezone_station = ExclusionZone(zone_id=station_zone_id, exclusivity=exclusivity)
            dbsession.add(ezone_station)
            dbsession.flush()
            dbsession.refresh(ezone_station)


def add_linked_gates_table(dbsession, fleet):
    ez_path = os.path.join(f"{os.environ['FM_MAP_DIR']}", f"{fleet}", "map", "ez.json")
    if not os.path.exists(ez_path):
        return
    with open(ez_path, "r") as f:
        ez_gates = json.load(f)
        gates_dict = ez_gates["ez_gates"]
        for gate in gates_dict.values():
            if gate["linked_gate"]:
                zone_types = ["_lane", "_station"]
                for zone_type_1 in zone_types:
                    print(f"Current gate {gate}!")
                    prev_zone_id = gate["name"] + zone_type_1
                    linked_gates = gate["linked_gates_ids"]
                    print(f"Adding linked gates for {prev_zone_id}!")
                    print(f"linked_gates are {linked_gates}!")
                    for linked_gate in linked_gates:
                        for zone_type_2 in zone_types:
                            linked_gate_id = (
                                gates_dict[str(linked_gate)]["name"] + zone_type_2
                            )
                            print(f"linked_gate_id is {linked_gate_id}!")
                            try:
                                _ = (
                                    dbsession.query(LinkedGates)
                                    .filter(LinkedGates.prev_zone_id == prev_zone_id)
                                    .filter(LinkedGates.next_zone_id == linked_gate_id)
                                ).one()
                                print(
                                    f"link between {prev_zone_id} and {linked_gate_id} already exists"
                                )
                            except Exception as e:
                                new_linked_gate = LinkedGates(
                                    prev_zone_id=prev_zone_id, next_zone_id=linked_gate_id
                                )
                                dbsession.add(new_linked_gate)
                                dbsession.flush()
                                dbsession.refresh(new_linked_gate)
                                print(
                                    f"created a link between {prev_zone_id} and {linked_gate_id}"
                                )
    return


def add_update_frontend_user(user_name: str, hashed_password: str, role: str):
    with session_maker() as db:
        try:
            user: FrontendUser = (
                db.query(FrontendUser).filter(FrontendUser.name == user_name).one()
            )
            user.hashed_password = hashed_password
            user.role = role
            print(f"updated frontend user successfully {user.__dict__}")
        except NoResultFound:
            user = FrontendUser(name=user_name, hashed_password=hashed_password, role=role)
            db.add(user)
            db.flush()
            db.refresh(user)
            print(f"added frontend user successfully {user.__dict__}")
        db.commit()


def create_all_tables():
    all_files = glob.glob("models/*.py")
    for file in all_files:
        module = file.split(".")[0]
        module = module.replace("/", ".")
        print(f"looking for models in module: {module}")
        try:
            models = importlib.import_module(module)
            models.Base.metadata.create_all(bind=engine)
            print(f"created tables from {module}")
        except Exception as e:
            print(f"failed to create tables from {module}, {e}")


def create_table(model):
    model.__table__.metadata(bind=engine)


def get_all_table_names():
    inspector = sql_inspect(engine)
    all_table_names = inspector.get_table_names("public")
    return all_table_names


def delete_table_contents(Model):
    with session_maker() as db:
        _ = db.query(Model).delete()
        db.commit()


BUF_SIZE = 65536


def get_filenames(directory):
    """
    This function will generate the file names in a directory, and ignores any sub-directories
    """
    file_names = []
    flist = os.listdir(directory)
    for item in flist:
        if item[0] == ".":
            # must be a meta file, ignoring this
            continue
        if os.path.isdir(directory + "/" + item):
            # this is a directory, not a file. ignoring
            continue
        file_names.append(item)  # Add it to the list.
    print(f"{directory} filenames: {file_names}")
    return file_names


def maybe_delete_file(fpath):
    if os.path.isfile(fpath):  # file exists
        try:
            os.remove(fpath)
            print(f"Deleted {fpath} file!")
        except Exception as e:
            print(f"Couldn't delete {fpath}. {e}")
    else:
        print(f"{fpath} doesn't exist!")
    return


def create_map_files_txt(fleet_name):
    fleet_path = os.path.join(os.environ["FM_MAP_DIR"], f"{fleet_name}/map")
    map_files_path = fleet_path + "/map_files.txt"
    maybe_delete_file(map_files_path)
    flist = get_filenames(fleet_path)
    with open(map_files_path, "w") as fp:
        for item in flist:
            vals = f"{item}\n"
            # write each item on a new line
            fp.write(vals)
    print(f"Created new {map_files_path} with {flist}")
    return


def maybe_create_gmaj_file(fleet_name):
    gmaj_path = os.path.join(
        os.environ["FM_MAP_DIR"], f"{fleet_name}/map/grid_map_attributes.json"
    )
    if os.path.isfile(gmaj_path):
        print(f"Found the GMAJ file {gmaj_path}!")
        return
    else:
        print(f"Couldn't find the GMAJ file {gmaj_path}, will generate one now!")
        map_path = gmaj_path = os.path.join(os.environ["FM_MAP_DIR"], f"{fleet_name}/map/")
        gmac.create_gmaj(map_path, gmaj_path)
        print(f"Created a new GMAJ file {gmaj_path}!")
    return


def maybe_create_graph_object(fleet_name):
    graph_object_path = os.path.join(
        os.environ["FM_MAP_DIR"], f"{fleet_name}/map/graph_object.json"
    )
    gmaj_path = os.path.join(
        os.environ["FM_MAP_DIR"], f"{fleet_name}/map/grid_map_attributes.json"
    )
    with open(gmaj_path, "r") as f:
        gma = json.load(f)

    # get terminal lines and stations object from json dict
    terminal_lines = gma["terminal_lines_info"]
    stations = gma["stations_info"]
    terminal_lines_int = rpi.process_dict(terminal_lines)
    stations_objects = rpi.process_stations_info(stations)
    gbu.maybe_build_graph_object_json(
        terminal_lines_int,
        stations_objects,
        gmaj_path=gmaj_path,
        graph_object_path=graph_object_path,
    )
    return


def update_delete_stations(dbsession, grid_map_attributes_path, fleet_id):
    with open(grid_map_attributes_path) as f:
        gmas = json.load(f)
        stations_info = gmas["stations_info"]
        valid_stations = []
        for _, station_info in stations_info.items():
            valid_stations.append(station_info["station_name"])
            add_update_station(dbsession, station_info, fleet_id)

        print(f"valid stations: {valid_stations} fleet_id: {fleet_id}")
        print("will delete stations not present in valid_stations list from the db")

        # delete stations removed from gmaj
        invalid_stations_status = (
            dbsession.query(StationStatus)
            .join(StationStatus.station)
            .filter(Station.fleet_id == fleet_id)
            .filter(not_(StationStatus.station_name.in_(valid_stations)))
            .all()
        )
        for st_status in invalid_stations_status:
            dbsession.delete(st_status)

        invalid_stations = (
            dbsession.query(Station)
            .filter(Station.fleet_id == fleet_id)
            .filter(not_(Station.name.in_(valid_stations)))
            .all()
        )
        for st in invalid_stations:
            dbsession.delete(st)


def reset_fleet(dbsession, fleet_name: str):
    fleet_obj: Fleet = dbsession.get_fleet(fleet_name)
    fleet_id = fleet_obj.id

    grid_map_attributes_path = os.path.join(
        f"{os.environ['FM_MAP_DIR']}", f"{fleet_name}", "map", "grid_map_attributes.json"
    )

    if not os.path.exists(grid_map_attributes_path):
        raise ValueError("gmaj not available")

    maybe_update_map_files(fleet_name)
    add_update_map_files(dbsession.session, fleet_name)
    update_delete_stations(dbsession.session, grid_map_attributes_path, fleet_id)

    # remove gate not needed removing gate from ez.json should do

    add_exclusion_zones(dbsession.session, fleet_name)
    add_linked_gates_table(dbsession.session, fleet_name)


def maybe_update_map_files(fleet_name):
    maybe_create_graph_object(fleet_name)


def compute_sha1_hash(fpath):
    sha1 = hashlib.sha1()
    with open(fpath, "rb") as f:
        while True:
            data = f.read(BUF_SIZE)
            if not data:
                break
            sha1.update(data)
    return sha1.hexdigest()
