import hashlib
import os
import sys
import secrets
import logging
import logging.config
import json
import glob
import importlib
import datetime
from typing import List, Dict
from core.db import engine
from core.constants import FleetStatus

from sqlalchemy import inspect as sql_inspect
from sqlalchemy import or_
from sqlalchemy.sql import not_
from sqlalchemy.orm.attributes import flag_modified
from models.db_session import DBSession
import models.fleet_models as fm
import models.visa_models as vm
from models.frontend_models import FrontendUser
from models.base_models import StationProperties


# setup logging
log_conf_path = os.path.join(os.getenv("FM_CONFIG_DIR"), "logging.conf")
logging.config.fileConfig(log_conf_path)
logger = logging.getLogger("configure_fleet")

logging.getLogger().level == logging.ERROR
sys.path.append(os.environ["MULE_ROOT"])
import mule.ati.tools.gmaj_creator as gmac
import mule.ati.control.bridge.router_planner_interface as rpi
import mule.ati.control.dynamic_router.graph_builder_utils as gbu

# utils are collection of functions and classes which have common patterns.
# this module contains frequently used functions by fleet.


def gen_api_key(hwid: str) -> str:
    return secrets.token_urlsafe(32) + "_" + hwid


def create_all_tables() -> None:
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
    return


def create_table(model) -> None:
    model.__table__.metadata(bind=engine)
    return


def get_all_table_names():
    inspector = sql_inspect(engine)
    all_table_names = inspector.get_table_names("public")
    return all_table_names


def compute_sha1_hash(fpath: str) -> str:
    BUF_SIZE = 65536
    sha1 = hashlib.sha1()
    with open(fpath, "rb") as f:
        while True:
            data = f.read(BUF_SIZE)
            if not data:
                break
            sha1.update(data)
    return sha1.hexdigest()


def get_map_file_path(fleet_name: str, file_name: str) -> str:
    return os.path.join(
        f"{os.environ['FM_MAP_DIR']}", f"{fleet_name}", "map", f"{file_name}"
    )


def get_map_path(fleet_name: str) -> str:
    return os.path.join(f"{os.environ['FM_MAP_DIR']}", f"{fleet_name}", "map")


def get_filenames(directory: str) -> List:
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
    return file_names


def maybe_update_map_files(fleet_name: str) -> None:
    maybe_create_gmaj_file(fleet_name)
    maybe_create_graph_object(fleet_name)
    return


def maybe_create_gmaj_file(fleet_name: str) -> None:
    gmaj_path = get_map_file_path(fleet_name, "grid_map_attributes.json")
    wpsj_path = get_map_file_path(fleet_name, "waypoints.json")
    rpi.maybe_update_gmaj(gmaj_path, wpsj_path, True)
    return


def maybe_create_graph_object(fleet_name: str) -> None:
    graph_object_path = get_map_file_path(fleet_name, "graph_object.json")
    gmaj_path = get_map_file_path(fleet_name, "grid_map_attributes.json")

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


class FrontendUserUtils:
    @classmethod
    def add_update_frontend_user(
        cls, dbsession: DBSession, user_name: str, hashed_password: str, role: str
    ) -> None:
        user: FrontendUser = (
            dbsession.session.query(FrontendUser)
            .filter(FrontendUser.name == user_name)
            .one_or_none()
        )
        if user:
            user.hashed_password = hashed_password
            user.role = role
            logger.info(
                f"updated FrontendUser {user_name}, with role: {role}, hashed_password: {hashed_password}"
            )

        else:
            user = FrontendUser(name=user_name, hashed_password=hashed_password, role=role)
            logger.info(
                f"added FrontendUser {user_name}, with role: {role}, hashed_password: {hashed_password}"
            )
            dbsession.add_to_session(user)

    @classmethod
    def delete_frontend_user(cls, dbsession: DBSession, user_name: str):
        user: FrontendUser = (
            dbsession.session.query(FrontendUser)
            .filter(FrontendUser.name == user_name)
            .one_or_none()
        )
        if user:
            dbsession.session.delete(user)
            logger.info(
                f"deleted FrontendUser {user_name}, with role: {role}, hashed_password: {hashed_password}"
            )
        else:
            raise ValueError(f"FrontendUser {user_name} not found")

    @classmethod
    def delete_all_frontend_users(cls, dbsession: DBSession):
        _ = dbsession.session.query(FrontendUser).delete()


class FleetUtils:
    @classmethod
    def add_fleet(
        cls, dbsession: DBSession, name: str, site: str, location: str, customer: str
    ):
        fleet: fm.Fleet = (
            dbsession.session.query(fm.Fleet).filter(fm.Fleet.name == name).one_or_none()
        )
        if fleet:
            fleet.site = site
            fleet.location = location
            fleet.customer = customer
            logger.info(
                f"updated fleet {name}, site: {site}, location: {location}, customer: {customer}"
            )
        else:
            map: fm.Map = (
                dbsession.session.query(fm.Map).filter(fm.Map.name == name).one_or_none()
            )
            if map is None:
                raise ValueError("Add map before adding fleet")
            fleet = fm.Fleet(
                name=name,
                site=site,
                location=location,
                customer=customer,
                status=FleetStatus.STARTED,
                map_id=map.id,
            )
            dbsession.add_to_session(fleet)
            logger.info(
                f"added fleet {name}, site: {site}, location: {location}, customer: {customer}"
            )

            optimal_dispatch_state = fm.OptimalDispatchState(
                fleet_name=name, last_assignment_time=datetime.datetime.now()
            )
            dbsession.add_to_session(optimal_dispatch_state)
            logger.info(f"added optimal_dispatch_state for fleet {name}")

    @classmethod
    def add_map(cls, dbsession: DBSession, fleet_name: str):
        maybe_update_map_files(fleet_name=fleet_name)
        map = (
            dbsession.session.query(fm.Map).filter(fm.Map.name == fleet_name).one_or_none()
        )
        if map is None:
            map: fm.Map = fm.Map(name=fleet_name)
            dbsession.add_to_session(map)
            logger.info(f"added map {fleet_name}")
        cls.add_update_map_files(dbsession, fleet_name, map.id)

    @classmethod
    def add_update_map_files(cls, dbsession: DBSession, fleet_name: str, map_id: int):
        map_path = get_map_path(fleet_name)
        map_files = get_filenames(map_path)
        valid_map_files = []
        for map_file_name in map_files:
            map_file_name = map_file_name.rstrip()
            map_file_path = f"{map_path}/{map_file_name}"
            sha1 = compute_sha1_hash(map_file_path)
            map_file: fm.MapFile = (
                dbsession.session.query(fm.MapFile)
                .filter(fm.MapFile.map_id == map_id)
                .filter(fm.MapFile.filename == map_file_name)
                .one_or_none()
            )
            valid_map_files.append(map_file_name)
            if map_file:
                logger.info(
                    f"updated shasum of the file {map_file.filename} @ {map_file_path}.. shasum: {sha1}"
                )
                map_file.file_hash = sha1
            else:
                map_file = fm.MapFile(map_id=map_id, filename=map_file_name, file_hash=sha1)
                logger.info(f"added {map_file.filename} @ {map_file_path}..shasum: {sha1}")
                dbsession.add_to_session(map_file)

        all_invalid_map_files = (
            dbsession.session.query(fm.MapFile)
            .filter(fm.MapFile.map_id == map_id)
            .filter(not_(fm.MapFile.filename.in_(valid_map_files)))
            .all()
        )
        logger.info(f"invalid files with map_id: {map_id}: {all_invalid_map_files} ")
        for invalid_file in all_invalid_map_files:
            logger.info(
                f"deleting {invalid_file.filename} entry from map_files wih map_id: {map_id}"
            )
            dbsession.session.delete(invalid_file)

    @classmethod
    def delete_map(cls, dbsession: DBSession, map_id: int):
        dbsession.session.query(fm.MapFile).filter(fm.MapFile.map_id == map_id).delete()
        dbsession.session.query(fm.Map).filter(fm.Map.id == map_id).delete()
        logger.info(f"Successfully deleted map, all map_files with map_id: {map_id}")

    @classmethod
    def update_stations_in_map(cls, dbsession: DBSession, fleet_name: str, fleet_id: int):
        # maybe_update_map_files(fleet_name=fleet_name)
        gmaj_path = get_map_file_path(fleet_name, "grid_map_attributes.json")
        if not os.path.exists(gmaj_path):
            raise ValueError(f"GMAJ doesn't exists for {fleet_name}")

        with open(gmaj_path) as f:
            gmas = json.load(f)
            stations_info = gmas["stations_info"]
            valid_stations = []
            for _, station_info in stations_info.items():
                cls.add_edit_station(dbsession, station_info, fleet_id)
                valid_stations.append(station_info["station_name"])

            logger.info(f"valid stations for fleet: {fleet_name}: {valid_stations}")

            cls.delete_invalid_stations(dbsession, fleet_id, valid_stations)

    @classmethod
    def add_edit_station(cls, dbsession: DBSession, station_info: Dict, fleet_id: int):
        properties = []
        for tag in station_info["station_tags"]:
            try:
                properties.append(getattr(StationProperties, tag.upper()))
            except Exception as e:
                logger.info(f"unable to add station properties, {e}")

        station_name = station_info["station_name"]
        station_pose = station_info["pose"]
        station: fm.Station = (
            dbsession.session.query(fm.Station).filter_by(name=station_name).one_or_none()
        )

        if station:
            if station.fleet_id != fleet_id:
                raise ValueError(
                    "Station names cannot be repeated, two fleets cannot have same station names"
                )
            station.pose = station_info["pose"]
            station.properties = properties
            logger.info(
                f"updated {station_name} with pose: {station.pose},  properties: {station.properties}"
            )

        else:
            station = fm.Station(
                name=station_name,
                pose=station_pose,
                properties=properties,
                fleet_id=fleet_id,
            )
            dbsession.add_to_session(station)
            logger.info(
                f"added {station_name} to fleet_id: {fleet_id}, with pose: {station.pose}, properties: {station.properties}"
            )

            station_status = fm.StationStatus(
                station_name=station_name, disabled=False, arriving_sherpas=[]
            )
            logger.info(f"added station status entry for {station_name}")
            dbsession.add_to_session(station_status)

    @classmethod
    def delete_station_status(cls, dbsession: DBSession, station_name: str):
        station_status = dbsession.get_station_status(station_name)
        dbsession.session.delete(station_status)
        logger.info(
            f"deleted station status entry for station: {station_status.station_name}"
        )

    @classmethod
    def delete_station(cls, dbsession: DBSession, station_name: str):
        station = dbsession.get_station(station_name)
        dbsession.session.delete(station)
        logger.info(f"deleted station: {station_name}")

    @classmethod
    def delete_invalid_stations(
        cls, dbsession: DBSession, fleet_id: int, valid_stations: List[str]
    ):
        invalid_station = (
            dbsession.session.query(fm.Station)
            .filter(fm.Station.fleet_id == fleet_id)
            .filter(not_(fm.Station.name.in_(valid_stations)))
            .all()
        )
        for st in invalid_station:
            cls.delete_station_status(dbsession, st.name)
            cls.delete_station(dbsession, st.name)

    @classmethod
    def delete_fleet(cls, dbsession: DBSession, fleet_name: str):
        fleet: fm.Fleet = dbsession.get_fleet(fleet_name)
        all_station: List[fm.Station] = dbsession.get_all_stations_in_fleet(fleet_name)
        for station in all_station:
            cls.delete_station_status(dbsession, station.name)
            cls.delete_station(dbsession, station.name)

        ExclusionZoneUtils.delete_exclusion_zones(dbsession, fleet_name)
        map_ip = fleet.map_id

        # delete optimal dispatch state
        dbsession.session.query(fm.OptimalDispatchState).filter(
            fm.OptimalDispatchState.fleet_name == fleet_name
        ).delete()
        logger.info(f"deleted OptimalDispatchState for fleet {fleet_name}")

        dbsession.session.delete(fleet)
        logger.info(f"deleted fleet {fleet_name}")
        cls.delete_map(dbsession, map_ip)


class SherpaUtils:
    @classmethod
    def add_edit_sherpa(
        cls,
        dbsession: DBSession,
        sherpa_name: str,
        hwid=None,
        ip_address=None,
        api_key=None,
        fleet_id=None,
    ):
        sherpa: fm.Sherpa = (
            dbsession.session.query(fm.Sherpa)
            .filter(fm.Sherpa.name == sherpa_name)
            .one_or_none()
        )

        if hwid is None:
            raise ValueError("Cannot add a sherpa without hwid")

        if api_key is None:
            api_key = gen_api_key(hwid)
            logger.info(f"generated api_key {api_key} for {sherpa_name} with {hwid}")

        hashed_api_key = hashlib.sha256(api_key.encode("utf-8")).hexdigest()
        if sherpa:
            sherpa.hwid = hwid
            sherpa.ip_address = None
            sherpa.api_key = api_key
            if sherpa.fleet_id != fleet_id:
                raise ValueError(
                    "Cannot edit fleet_id for sherpa object. Delete sherpa,  add it to a different fleet"
                )
            logger.info(
                f"updated sherpa {sherpa_name}, with hwid: {hwid}, api_key: {api_key}"
            )
        else:
            sherpa: fm.Sherpa = fm.Sherpa(
                name=sherpa_name,
                hwid=hwid,
                ip_address=None,
                hashed_api_key=hashed_api_key,
                fleet_id=fleet_id,
            )
            dbsession.add_to_session(sherpa)
            logger.info(
                f"added sherpa {sherpa_name}, with hwid: {hwid}, api_key: {api_key}"
            )
            cls.add_sherpa_status(dbsession, sherpa.name)
            cls.set_availability(dbsession, sherpa.name, sherpa.fleet.name)

    @classmethod
    def add_sherpa_status(cls, dbsession, sherpa_name, other_info={}):
        sherpa_status: fm.SherpaStatus = fm.SherpaStatus(
            sherpa_name=sherpa_name, other_info={}
        )
        dbsession.add_to_session(sherpa_status)
        logger.info(f"added sherpa status entry for sherpa: {sherpa_name}")

    @classmethod
    def set_availability(cls, dbsession, sherpa_name, fleet_name, available=False):
        sherpa_availability: fm.AvailableSherpas = (
            dbsession.session.query(fm.AvailableSherpas)
            .filter(fm.AvailableSherpas.sherpa_name == sherpa_name)
            .one_or_none()
        )
        if sherpa_availability:
            sherpa_availability.available = available
            logger.info(
                f"updated sherpa availability entry for sherpa: {sherpa_name}, available: {available}"
            )

        else:
            sherpa_availability = fm.AvailableSherpas(
                sherpa_name=sherpa_name,
                fleet_name=fleet_name,
                available=available,
            )
            dbsession.add_to_session(sherpa_availability)
            logger.info(
                f"added sherpa availability entry for sherpa: {sherpa_name}, available: {available}"
            )

    @classmethod
    def delete_sherpa(cls, dbsession, sherpa_name):
        # delete sherpa status object
        sherpa_status: fm.SherpaStatus = dbsession.get_sherpa_status(sherpa_name)

        if not sherpa_status:
            raise ValueError(f"Sherpa {sherpa_name} not found")

        sherpa: fm.Sherpa = sherpa_status.sherpa

        dbsession.session.delete(sherpa_status)
        logger.info(f"deleted sherpa status entry for sherpa: {sherpa_name}")

        # delete sherpa object
        dbsession.session.delete(sherpa)
        logger.info(f"deleted sherpa {sherpa_name}")

        # delete available sherpa
        available_sherpa = (
            dbsession.session.query(fm.AvailableSherpas)
            .filter(fm.AvailableSherpas.sherpa_name == sherpa_name)
            .one()
        )
        dbsession.session.delete(available_sherpa)

        logger.info(f"deleted sherpa availability entry for sherpa: {sherpa_name}")


class ExclusionZoneUtils:
    @classmethod
    def add_exclusion_zones(cls, dbsession: DBSession, fleet_name: str):
        ez_path = get_map_file_path(fleet_name, "ez.json")
        if not os.path.exists(ez_path):
            return
        with open(ez_path, "r") as f:
            ez_gates = json.load(f)

        for gate in ez_gates["ez_gates"].values():
            gate_name = gate["name"]
            zone_ids_to_add = [f"{gate_name}_lane", f"{gate_name}_station"]
            # exclusivity = gate["exclusive_parking"]
            for zone_id in zone_ids_to_add:
                ezone: vm.ExclusionZone = (
                    dbsession.session.query(vm.ExclusionZone)
                    .filter_by(zone_id=zone_id)
                    .one_or_none()
                )
                if ezone:
                    logger.info(f"ExclusionZone {zone_id} already present")
                    logger.info(f"ExclusionZone serving fleets {ezone.fleets}")
                    if fleet_name not in ezone.fleets:
                        logger.info(f"added {fleet_name} to ezone.fleets for {zone_id}")
                        ezone.fleets.append(fleet_name)
                        logger.info(f"ExclusionZone serving fleets {ezone.fleets}")
                        flag_modified(ezone, "fleets")
                else:
                    ezone: vm.ExclusionZone = vm.ExclusionZone(
                        zone_id=zone_id, fleets=[fleet_name]
                    )
                    dbsession.add_to_session(ezone)
                    logger.info(f"Added exclusionZone {zone_id}")
                    logger.info(f"ExclusionZone serving fleets {ezone.fleets}")

    @classmethod
    def add_linked_gates(cls, dbsession: DBSession, fleet_name: str):
        ez_path = get_map_file_path(fleet_name, "ez.json")
        if not os.path.exists(ez_path):
            return
        with open(ez_path, "r") as f:
            ez_gates = json.load(f)

        gates_dict = ez_gates["ez_gates"]
        for gate in gates_dict.values():
            gate_name = gate["name"]
            if not gate["linked_gate"]:
                logger.info(f"Gate {gate_name} has no linked gates")
                continue

            linked_gates = gate["linked_gates_ids"]
            logger.info(f"Gate {gate_name} has linked gates: {linked_gates}")
            prev_zone = gate_name
            for linked_gate in linked_gates:
                next_zone = gates_dict[str(linked_gate)]["name"]
                cls.create_links_between_zones(dbsession, prev_zone, next_zone)

    @classmethod
    def create_links_between_zones(cls, dbsession: DBSession, prev_zone, next_zone):
        zone_types = ["_lane", "_station"]
        for zone_type in zone_types:
            prev_zone_id = prev_zone + zone_type
            next_zone_st = next_zone + "_station"
            next_zone_lane = next_zone + "_lane"
            lane_link = (
                dbsession.session.query(vm.LinkedGates)
                .filter(vm.LinkedGates.prev_zone_id == prev_zone_id)
                .filter(vm.LinkedGates.next_zone_id == next_zone_lane)
                .one_or_none()
            )
            st_link = (
                dbsession.session.query(vm.LinkedGates)
                .filter(vm.LinkedGates.prev_zone_id == prev_zone_id)
                .filter(vm.LinkedGates.next_zone_id == next_zone_st)
                .one_or_none()
            )

            if lane_link:
                logger.info(
                    f"Link between {prev_zone_id} and {next_zone_lane} already exsists"
                )
            else:
                lane_link = vm.LinkedGates(
                    prev_zone_id=prev_zone_id, next_zone_id=next_zone_lane
                )
                dbsession.add_to_session(lane_link)
                logger.info(f"Created a link between {prev_zone_id} and {next_zone_lane}")

            if st_link:
                logger.info(
                    f"Link between {prev_zone_id} and {next_zone_st} already exsists"
                )
            else:
                st_link = vm.LinkedGates(
                    prev_zone_id=prev_zone_id, next_zone_id=next_zone_st
                )
                dbsession.add_to_session(st_link)
                logger.info(f"Created a link between {prev_zone_id} and {next_zone_st}")

    @classmethod
    def delete_exclusion_zones(cls, dbsession: DBSession, fleet_name: str):
        all_ezones: List[vm.ExclusionZone] = dbsession.session.query(vm.ExclusionZone).all()
        for ezone in all_ezones:
            if fleet_name in ezone.fleets:
                ezone.fleets.remove(fleet_name)
                if len(ezone.fleets) == 0:
                    cls.delete_links(dbsession, ezone)
                    dbsession.session.delete(ezone)
                    logger.info(f"deleted ezone {ezone.zone_id}")
                flag_modified(ezone, "fleets")

    @classmethod
    def delete_links(cls, dbsession: DBSession, ezone: vm.ExclusionZone):
        all_links = (
            dbsession.session.query(vm.LinkedGates)
            .filter(
                or_(
                    vm.LinkedGates.prev_zone_id == ezone.zone_id,
                    vm.LinkedGates.next_zone_id == ezone.zone_id,
                )
            )
            .all()
        )
        for link in all_links:
            logger.info(f"deleted link between {link.prev_zone_id} and {link.next_zone_id}")
            dbsession.session.delete(link)
