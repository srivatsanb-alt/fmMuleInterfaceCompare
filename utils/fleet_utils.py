import hashlib
import os
import sys
import secrets
import logging
import logging.config
import json
import time
import datetime
from typing import List, Dict
from core.constants import FleetStatus
from sqlalchemy import or_
from sqlalchemy.sql import not_
from sqlalchemy.orm.attributes import flag_modified
import zipfile
import tarfile
from fastapi import HTTPException

# ati code imports
from models.db_session import DBSession
from models.mongo_client import FMMongo
import models.fleet_models as fm
import models.visa_models as vm
import models.misc_models as mm
import models.trip_models as tm
from models.base_models import StationProperties
import utils.log_utils as lu


# setup logging
logging.config.dictConfig(lu.get_log_config_dict())
logger = logging.getLogger("configure_fleet")

logging.getLogger().level == logging.ERROR
sys.path.append(os.environ["MULE_ROOT"])


def gen_api_key(hwid: str) -> str:
    return secrets.token_urlsafe(32) + "_" + hwid


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
        f"{os.environ['FM_STATIC_DIR']}", f"{fleet_name}", "map", f"{file_name}"
    )


def get_map_path(fleet_name: str) -> str:
    return os.path.join(f"{os.environ['FM_STATIC_DIR']}", f"{fleet_name}", "map")


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


def load_ez_json(fleet_name):
    ez_path = get_map_file_path(fleet_name, "ez.json")
    if not os.path.exists(ez_path):
        return None

    with open(ez_path, "r") as f:
        try:
            ez_gates = json.load(f)
        except Exception as e:
            raise Exception(f"Unable to parse ez.json, Exception: {e}")

    return ez_gates


def is_reset_fleet_required(fleet_name, map_files):
    fleet_path = os.path.join(os.environ["FM_STATIC_DIR"], f"{fleet_name}/map")
    for mf in map_files:
        file_path = f"{fleet_path}/{mf.filename}"
        try:
            filehash = compute_sha1_hash(file_path)
            if filehash != mf.file_hash:
                return True
        except Exception as e:
            logging.getLogger().info(
                f"Unable to find the shasum of file {file_path}, exception: {e}"
            )
            return True
    return False


def maybe_update_map_files(fleet_name: str) -> None:
    maybe_create_gmaj_file(fleet_name)
    maybe_create_graph_object(fleet_name)
    return


def maybe_create_gmaj_file(fleet_name: str) -> None:
    # importing inside func call - initializes glob vars
    import mule.ati.control.bridge.router_planner_interface as rpi

    gmaj_path = get_map_file_path(fleet_name, "grid_map_attributes.json")
    wpsj_path = get_map_file_path(fleet_name, "waypoints.json")

    if not os.path.exists(wpsj_path):
        raise Exception(f"Unable to fetch {wpsj_path}")

    rpi.maybe_update_gmaj(gmaj_path, wpsj_path, True)
    return


def maybe_create_graph_object(fleet_name: str) -> None:
    # importing inside func call - initializes glob vars
    import mule.ati.control.bridge.router_planner_interface as rpi
    import mule.ati.control.dynamic_router.graph_builder_utils as gbu

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


def add_software_compatability(dbsession: DBSession):
    software_compatability = dbsession.get_compatability_info()

    if software_compatability is None:
        sc = mm.SoftwareCompatability(info={"sherpa_versions": []})
        dbsession.add_to_session(sc)


def add_sherpa_metadata(dbsession: DBSession):
    all_sherpas = dbsession.get_all_sherpas()
    for sherpa in all_sherpas:
        sherpa_metadata = dbsession.get_sherpa_metadata(sherpa.name)
        if sherpa_metadata is None:
            sm = fm.SherpaMetaData(sherpa_name=sherpa.name, info={"can_edit": "True"})
            dbsession.add_to_session(sm)


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
                raise Exception("Add map before adding fleet")
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

        if not os.path.exists(map_path):
            raise ValueError(f"Unable to fetch files from {map_path}")

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
            raise ValueError(f"grip map attributes files doesn't exists for {fleet_name}")

        with open(gmaj_path) as f:
            gmas = json.load(f)
            stations_info = gmas["stations_info"]
            valid_stations = []
            for _, station_info in stations_info.items():
                if station_info["station_name"] in valid_stations:
                    raise ValueError(
                        f"Station: {station_info['station_name']} is already present in fleet"
                    )
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
                    f"Station: {station_name} is repeated, two fleets cannot have same station names"
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
            cls.delete_invalid_booked_trips(dbsession, st.name, st.fleet.name)

    @classmethod
    def delete_invalid_booked_trips(cls, dbsession, station_name, fleet_name):
        p_trips = dbsession.get_pending_trips_with_fleet_name(fleet_name)
        for p_trip in p_trips:
            if station_name in p_trip.trip.route:
                logger.info(
                    f"deleted trip {p_trip.trip.id}, reason: Invalid route, {station_name} will be removed with the map change"
                )
                dbsession.delete_pending_trip(p_trip)
                p_trip.trip.status = tm.TripStatus.CANCELLED

    @classmethod
    def delete_saved_routes(cls, dbsession: DBSession, fleet_name: str):
        dbsession.session.query(tm.SavedRoutes).filter(
            tm.SavedRoutes.fleet_name == fleet_name
        ).delete()

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
        cls.delete_saved_routes(dbsession, fleet_name)


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
        sherpa_type=None,
        is_add=True,
    ):
        sherpa: fm.Sherpa = (
            dbsession.session.query(fm.Sherpa)
            .filter(fm.Sherpa.name == sherpa_name)
            .one_or_none()
        )

        if hwid is None:
            raise ValueError("Cannot add a sherpa without hwid")

        if api_key is not None and is_add is True:
            hashed_api_key = hashlib.sha256(api_key.encode("utf-8")).hexdigest()
        else:
            hashed_api_key = api_key

        if sherpa:
            sherpa.hwid = hwid
            sherpa.ip_address = None
            sherpa.sherpa_type = sherpa_type
            if api_key is not None:
                sherpa.hashed_api_key = hashed_api_key
                logger.info(f"updated sherpa {sherpa_name} ")
            if sherpa.fleet_id != fleet_id and is_add is True:
                raise ValueError(
                    f"Cannot duplicate sherpas across fleet, {sherpa.name} is already present"
                )
            logger.info(f"updated sherpa {sherpa_name}, with hwid: {hwid}")
        else:
            # new sherpa requires an API key and Hardware ID
            if api_key is None or hwid is None:
                raise ValueError("API Key/Hardware id cannot be None")

            temp = dbsession.get_sherpa_with_hwid(hwid)
            if temp and is_add is True:
                raise ValueError(
                    f"Cannot duplicate hwid {temp.name} already has the inputted hwid"
                )

            temp = dbsession.get_sherpa_with_hashed_api_key(hashed_api_key)
            if temp and is_add is True:
                raise ValueError(
                    f"Cannot duplicate api_key {temp.name} already has the inputted api key"
                )

            sherpa: fm.Sherpa = fm.Sherpa(
                name=sherpa_name,
                hwid=hwid,
                ip_address=None,
                hashed_api_key=hashed_api_key,
                fleet_id=fleet_id,
                sherpa_type=sherpa_type,
            )
            dbsession.add_to_session(sherpa)
            logger.info(
                f"added sherpa {sherpa_name}, with hwid: {hwid}, api_key: {api_key}"
            )
            cls.add_sherpa_status(dbsession, sherpa.name)
            cls.add_sherpa_metadata(dbsession, sherpa.name)
            cls.set_availability(dbsession, sherpa.name, sherpa.fleet.name)

    @classmethod
    def add_sherpa_status(cls, dbsession, sherpa_name, other_info={}):
        sherpa_status: fm.SherpaStatus = fm.SherpaStatus(
            sherpa_name=sherpa_name, idle=True, other_info={}
        )
        dbsession.add_to_session(sherpa_status)
        logger.info(f"added sherpa status entry for sherpa: {sherpa_name}")

    @classmethod
    def add_sherpa_metadata(cls, dbsession, sherpa_name):
        sm = fm.SherpaMetaData(sherpa_name=sherpa_name, info={"can_edit": "True"})
        dbsession.add_to_session(sm)
        logger.info(f"added sherpa metadata entry for sherpa: {sherpa_name}")

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
    def delete_exclude_stations_route(cls, dbsession: DBSession, sherpa_name: str):
        dbsession.session.query(tm.SavedRoutes).filter(
            tm.SavedRoutes.tag == f"exclude_stations_{sherpa_name}"
        ).delete()
        logger.info(f"deleted route exclude_stations_{sherpa_name}")

    @classmethod
    def delete_sherpa_metadata(cls, dbsession: DBSession, sherpa_name: str):
        sherpa_metadata = dbsession.get_sherpa_metadata(sherpa_name)

        if sherpa_metadata is not None:
            can_edit = sherpa_metadata.info.get("can_edit", "True")
            if not eval(can_edit):
                raise ValueError("Cannot delete/edit sherpa can_edit set to False")

        dbsession.session.delete(sherpa_metadata)
        logger.info(f"deleted sherpa metadata entry for sherpa: {sherpa_name}")

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

        cls.delete_exclude_stations_route(dbsession, sherpa_name)
        cls.delete_sherpa_metadata(dbsession, sherpa_name)


class ExclusionZoneUtils:
    @classmethod
    def add_exclusion_zones(cls, dbsession: DBSession, fleet_name: str):

        ez_gates = load_ez_json(fleet_name)

        if ez_gates is None:
            return

        for gate, gate_details in ez_gates["ez_gates"].items():
            gate_name = gate_details["name"]
            zone_ids_to_add = [f"{gate_name}_lane", f"{gate_name}_station"]
            for zone_id in zone_ids_to_add:
                exclusivity = True

                """
                1. By default all stations are exclusive
                2. By default all lanes are non-exclusive
                3. If sez is present in gate_tags, the _lane will be made exclusive as well
                """

                gate_tags = gate_details.get("gate_tags")
                if gate_tags is None:
                    gate_tags = []

                if zone_id.endswith("_lane") and "sez" not in gate_tags:
                    exclusivity = False

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
                    ezone.exclusivity = exclusivity
                else:
                    ezone: vm.ExclusionZone = vm.ExclusionZone(
                        zone_id=zone_id, exclusivity=exclusivity, fleets=[fleet_name]
                    )
                    dbsession.add_to_session(ezone)
                    logger.info(f"Added exclusionZone {zone_id}")
                    logger.info(f"ExclusionZone serving fleets {ezone.fleets}")

    @classmethod
    def add_linked_gates(cls, dbsession: DBSession, fleet_name: str):

        ez_gates = load_ez_json(fleet_name)
        if ez_gates is None:
            return

        gates_dict = ez_gates["ez_gates"]
        for gate, gate_details in ez_gates["ez_gates"].items():
            gate_name = gate_details["name"]

            if gate_details.get("exclusive_parking", True) is True:
                cls.create_internal_link_between_station_and_lane(dbsession, gate_name)

            if not gate_details["linked_gate"]:
                logger.info(f"Gate {gate_name} has no linked gates")
                continue

            linked_gates = gate_details["linked_gates_ids"]
            logger.info(f"Gate {gate_name} has linked gates: {linked_gates}")
            prev_zone = gate_name

            for linked_gate in linked_gates:
                try:
                    next_zone = gates_dict[str(linked_gate)]["name"]
                except Exception as e:
                    raise ValueError(
                        f"No gate with id: {linked_gate}, check linked gate ids of gate: {gate_name}"
                    )
                cls.create_links_between_zones(dbsession, prev_zone, next_zone)

    @classmethod
    def create_internal_link_between_station_and_lane(
        cls, dbsession: DBSession, ezone_name
    ):
        ezone_st = ezone_name + "_station"
        ezone_lane = ezone_name + "_lane"

        internal_link = (
            dbsession.session.query(vm.LinkedGates)
            .filter(vm.LinkedGates.prev_zone_id == ezone_st)
            .filter(vm.LinkedGates.next_zone_id == ezone_lane)
            .one_or_none()
        )
        if internal_link:
            logger.info(
                f"Internal Link between {ezone_name} station and lane already exsists"
            )

        else:
            internal_link = vm.LinkedGates(prev_zone_id=ezone_st, next_zone_id=ezone_lane)
            dbsession.add_to_session(internal_link)
            logger.info(f"Created a internal link between {ezone_st} and {ezone_lane}")

    @classmethod
    def create_links_between_zones(cls, dbsession: DBSession, prev_zone, next_zone):
        zone_types = ["_lane", "_station"]
        for zone_type in zone_types:
            prev_zone_id = prev_zone + zone_type
            next_zone_id = next_zone + zone_type
            link = (
                dbsession.session.query(vm.LinkedGates)
                .filter(vm.LinkedGates.prev_zone_id == prev_zone_id)
                .filter(vm.LinkedGates.next_zone_id == next_zone_id)
                .one_or_none()
            )
            if link:
                logger.info(
                    f"Link between {prev_zone_id} and {next_zone_id} already exsists"
                )
            else:
                new_link = vm.LinkedGates(
                    prev_zone_id=prev_zone_id, next_zone_id=next_zone_id
                )
                dbsession.add_to_session(new_link)
                logger.info(f"Created a link between {prev_zone_id} and {next_zone_id}")

    @classmethod
    def delete_exclusion_zones(
        cls, dbsession: DBSession, fleet_name: str, update_map=False
    ):
        all_ezones: List[vm.ExclusionZone] = dbsession.session.query(vm.ExclusionZone).all()

        updatable_gate_names = []

        ez_gates = load_ez_json(fleet_name)
        if ez_gates is not None:
            for gate, gate_details in ez_gates["ez_gates"].items():
                updatable_gate_names.append(gate_details["name"])
        logger.info(f"Updatable gates: {updatable_gate_names}")

        for ezone in all_ezones:
            if fleet_name in ezone.fleets:
                ezone.fleets.remove(fleet_name)
                logger.info(f"removed {fleet_name} from fleets of ezone: {ezone.zone_id}")

                if len(ezone.fleets) == 0:
                    cls.delete_links(dbsession, ezone)
                    dbsession.session.delete(ezone)
                    logger.info(f"deleted ezone {ezone.zone_id}")

                elif ezone.zone_id.rsplit("_", 1)[0] in updatable_gate_names and update_map:
                    cls.delete_links(dbsession, ezone)
                    logger.info(f"deleted links of ezone: {ezone.zone_id}")

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


async def update_fleet_conf_in_redis(dbsession: DBSession, aredis_conn):
    all_sherpa_names = dbsession.get_all_sherpa_names()
    all_fleet_names = dbsession.get_all_fleet_names()
    await aredis_conn.set("all_sherpas", json.dumps(all_sherpa_names))
    await aredis_conn.set("all_fleet_names", json.dumps(all_fleet_names))
    await aredis_conn.set("send_conf_to_mfm_unix_dt", time.time())


def get_all_fleets_list_as_per_user(user_name):
    with FMMongo() as fm_mongo:
        user_query = {"name": user_name}
        user_details_db = fm_mongo.get_frontend_user_details(user_query)
    
    if user_details_db['role'] == 'support':
        with DBSession() as dbsession:
            fleet_names = dbsession.get_all_fleet_names()
            return fleet_names
    else:
        return user_details_db['fleet_names']
    

def strip_archive_extensions(filename):
    archive_extensions = [
        '.tar.gz', '.tar.bz2', '.tar.xz', 
        '.zip', '.tar', '.gz', '.bz2', 
        '.xz', '.7z', '.rar'
    ]
    for ext in archive_extensions:
        if filename.endswith(ext):
            return filename[:-len(ext)]
    return os.path.splitext(filename)[0]

async def save_map(map_file):
    dir_to_save = os.getenv("FM_STATIC_DIR")
    os.makedirs(dir_to_save, exist_ok=True)
    file_path = os.path.join(dir_to_save, map_file.filename)
    with open(file_path, "wb") as buffer:
        buffer.write(await map_file.read())

    logger.info(f"Attempting to extract archive: {file_path}")
    logger.info(f"Extraction destination: {dir_to_save}")

    file_name = strip_archive_extensions(map_file.filename)
    required_files = {f"{file_name}/map/webui_map.png", f"{file_name}/map/webui_map.json", f"{file_name}/map/waypoints.json"}

    if zipfile.is_zipfile(file_path):
        logger.info("Detected ZIP archive")
        archive_class = zipfile.ZipFile
        is_zip = True
    elif tarfile.is_tarfile(file_path):
        logger.info("Detected TAR archive")
        archive_class = tarfile.open
        is_zip = False
    else:
        logger.info(f"Unrecognized archive type: {file_path}")
        os.remove(file_path)
        raise ValueError(
            "Uploaded file is not a valid ZIP or TAR archive"
        )

    with archive_class(file_path, 'r' if is_zip else 'r:*') as archive:
        archive_files = set(archive.namelist() if is_zip else archive.getnames())
        missing_files = required_files - archive_files
        if missing_files:
            logger.info(f"Missing files: {missing_files}")
            os.remove(file_path)
            raise ValueError(
                f"The uploaded archive is missing required files: {missing_files}"
            )
        archive.extractall(dir_to_save)
        logger.info(f"Successfully extracted files to {dir_to_save}")
    os.remove(file_path)