from typing import Dict, List
from core.logs import get_logger
from models.db_session import DBSession
from models.fleet_models import SherpaStatus
from models.trip_models import OngoingTrip, Trip, TripLeg
from utils.util import generate_random_job_id
from utils.create_certs import generate_certs_for_sherpa
from utils.fleet_utils import compute_sha1_hash
from models.request_models import MapFileInfo
import json
import redis
import os
import time
import numpy as np

AVAILABLE = "available"


def assign_sherpa(trip: Trip, sherpa: str, session: DBSession):
    ongoing_trip = session.create_ongoing_trip(sherpa, trip.id)
    trip.assign_sherpa(sherpa)
    sherpa_status = session.get_sherpa_status(sherpa)
    sherpa_status.idle = False
    sherpa_status.trip_id = trip.id
    get_logger(sherpa).info(f"assigned trip id {trip.id} to {sherpa}")
    return ongoing_trip


def start_trip(ongoing_trip: OngoingTrip, session: DBSession):

    redis_conn = redis.from_url(os.getenv("FM_REDIS_URI"))

    # populate trip etas, need not be imported for every request
    sherpa_status = session.get_sherpa_status(ongoing_trip.sherpa_name)

    start_pose = sherpa_status.pose
    fleet_name = ongoing_trip.trip.fleet_name

    etas_at_start = []
    for station in ongoing_trip.trip.augmented_route:
        job_id = generate_random_job_id()
        end_pose = session.get_station(station).pose
        control_router_job = [start_pose, end_pose, fleet_name, job_id]
        redis_conn.set(f"control_router_job_{job_id}", json.dumps(control_router_job))

        while not redis_conn.get(f"result_{job_id}"):
            time.sleep(0.005)

        route_length = json.loads(redis_conn.get(f"result_{job_id}"))
        redis_conn.delete(f"result_{job_id}")

        get_logger(ongoing_trip.sherpa_name).info(
            f"route_length {control_router_job}- {route_length}"
        )

        if route_length == np.inf:
            reason = f"no route from {start_pose} to {end_pose}"
            get_logger(ongoing_trip.sherpa_name).info(
                f"trip {ongoing_trip.trip_id} with {ongoing_trip.sherpa_name} failed, reason: {reason}"
            )
            end_trip(ongoing_trip, False, session)
            return

        etas_at_start.append(route_length)
        start_pose = session.get_station(station).pose

    ongoing_trip.trip.etas_at_start = etas_at_start
    ongoing_trip.trip.etas = ongoing_trip.trip.etas_at_start

    ongoing_trip.trip.start()
    get_logger(ongoing_trip.sherpa_name).info(f"trip {ongoing_trip.trip_id} started")


def end_trip(ongoing_trip: OngoingTrip, success: bool, session: DBSession):
    ongoing_trip.trip.end(success)
    session.delete_ongoing_trip(ongoing_trip)
    sherpa_status = session.get_sherpa_status(ongoing_trip.sherpa_name)
    sherpa_status.idle = True
    sherpa_status.trip_id = None
    sherpa_status.trip_leg_id = None


def start_leg(ongoing_trip: OngoingTrip, session: DBSession) -> TripLeg:
    trip: Trip = ongoing_trip.trip
    trip_leg: TripLeg = session.create_trip_leg(
        trip.id, ongoing_trip.curr_station(), ongoing_trip.next_station()
    )
    ongoing_trip.start_leg(trip_leg.id)
    sherpa_name = ongoing_trip.sherpa_name

    if ongoing_trip.curr_station():
        update_leg_curr_station(ongoing_trip.curr_station(), sherpa_name, session)

    update_leg_next_station(ongoing_trip.next_station(), sherpa_name, session)

    return trip_leg


def end_leg(ongoing_trip: OngoingTrip):
    ongoing_trip.trip_leg.end()
    ongoing_trip.end_leg()


def update_leg_curr_station(curr_station_name: str, sherpa: str, session: DBSession):
    curr_station_status = session.get_station_status(curr_station_name)
    if not curr_station_status:
        return
    if sherpa in curr_station_status.arriving_sherpas:
        curr_station_status.arriving_sherpas.remove(sherpa)


def update_leg_next_station(next_station_name: str, sherpa: str, session: DBSession):
    next_station_status = session.get_station_status(next_station_name)
    if not next_station_status:
        return
    next_station_status.arriving_sherpas.append(sherpa)


def is_sherpa_available_for_new_trip(sherpa_status):
    reason = None
    if not reason and not sherpa_status.inducted:
        reason = "out of fleet"
    if not reason and sherpa_status.trip_id:
        reason = "not idle"
    if not reason and not sherpa_status.initialized:
        reason = "not initialized"
    if not reason:
        reason = AVAILABLE
    return reason == AVAILABLE, reason


def get_sherpa_availability(all_sherpa_status: List[SherpaStatus]):
    availability = {}

    for sherpa_status in all_sherpa_status:
        available, reason = is_sherpa_available_for_new_trip(sherpa_status)
        availability[sherpa_status.sherpa_name] = available, reason

    return availability


def get_conveyor_ops_info(trip_metadata):
    get_logger().info(
        f"will parse trip metadata for conveyor ops, Trip metadata: {trip_metadata}"
    )
    num_units = None
    if trip_metadata:
        conveyor_ops = trip_metadata.get("conveyor_ops", None)
        if conveyor_ops:
            num_units = trip_metadata.get("num_units", None)
    return num_units


def find_best_sherpa():
    all_sherpa_status: List[SherpaStatus] = session.get_all_sherpa_status()
    availability: Dict[str, str] = get_sherpa_availability(all_sherpa_status)
    get_logger().info(f"sherpa availability: {availability}")

    for name, (available, _) in availability.items():
        if available:
            get_logger().info(f"found {name}")
            return name

    return None


def update_map_file_info_with_certs(
    map_file_info, sherpa_hostname, sherpa_ip_address, ip_changed
):
    save_path = os.path.join(os.getenv("FM_MAP_DIR"), "certs")

    files_to_process = [
        os.path.join(save_path, filename)
        for filename in [f"{sherpa_hostname}_cert.pem", f"{sherpa_hostname}_key.pem"]
    ]

    if not all([os.path.exists(filename) for filename in files_to_process]) or ip_changed:
        get_logger().info(
            f"will generate new cert files, HOSTNAME {sherpa_hostname}, ip_address: {sherpa_ip_address}, ip_changed: {ip_changed}"
        )
        generate_certs_for_sherpa(sherpa_hostname, sherpa_ip_address, save_path)

    all_file_hash = []
    for file_path in files_to_process:
        all_file_hash.append(compute_sha1_hash(file_path))

    cert_files = [f"{sherpa_hostname}_cert.pem", f"{sherpa_hostname}_key.pem"]

    # hardcoding to 2
    for i in range(2):
        map_file_info.append(MapFileInfo(file_name=cert_files[i], hash=all_file_hash[i]))

    return map_file_info
