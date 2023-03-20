import json
import redis
import os
import time
import numpy as np
from typing import List
import datetime
import psutil
import pandas as pd
from rq import Worker


# ati code imports
from core.logs import get_logger
from core.config import Config
import core.constants as cc
from models.db_session import DBSession
import models.fleet_models as fm
import models.trip_models as tm
import models.request_models as rqm
import models.misc_models as mm
import utils.util as utils_util
from utils.create_certs import generate_certs_for_sherpa
from utils.fleet_utils import compute_sha1_hash


# Trip hutils
def assign_sherpa(dbsession: DBSession, trip: tm.Trip, sherpa: fm.Sherpa):
    ongoing_trip = dbsession.create_ongoing_trip(sherpa.name, trip.id)
    trip.assign_sherpa(sherpa.name)
    sherpa_status: fm.SherpaStatus = sherpa.status
    sherpa_status.idle = False
    sherpa_status.trip_id = trip.id
    get_logger(sherpa.name).info(
        f"{sherpa.name} assigned trip {trip.id} with route {trip.route}"
    )
    return ongoing_trip


# starts a trip


def start_trip(
    dbsession: DBSession,
    ongoing_trip: tm.OngoingTrip,
    sherpa: fm.Sherpa,
    all_stations: List[fm.Station],
):

    redis_conn = redis.from_url(os.getenv("FM_REDIS_URI"))
    sherpa_status: fm.SherpaStatus = sherpa.status
    start_pose = sherpa_status.pose
    fleet_name = ongoing_trip.trip.fleet_name

    etas_at_start = []
    for station in all_stations:
        job_id = utils_util.generate_random_job_id()
        end_pose = station.pose
        control_router_rl_job = [start_pose, end_pose, fleet_name, job_id]
        redis_conn.set(f"control_router_rl_job_{job_id}", json.dumps(control_router_rl_job))

        while not redis_conn.get(f"result_{job_id}"):
            time.sleep(0.005)

        route_length = json.loads(redis_conn.get(f"result_{job_id}"))
        redis_conn.delete(f"result_{job_id}")

        get_logger(ongoing_trip.sherpa_name).info(
            f"route_length {control_router_rl_job}- {route_length}"
        )

        if route_length == np.inf:
            reason = f"no route from {start_pose} to {end_pose}"
            trip_failed_log = f"trip {ongoing_trip.trip_id} failed, sherpa_name: {ongoing_trip.sherpa_name} , reason: {reason}"
            get_logger(ongoing_trip.sherpa_name).warning(trip_failed_log)

            dbsession.add_notification(
                [sherpa.name, sherpa.fleet.name],
                trip_failed_log,
                mm.NotificationLevels.alert,
                mm.NotificationModules.trip,
            )
            end_trip(dbsession, ongoing_trip, sherpa, False)
            return

        etas_at_start.append(route_length)
        start_pose = station.pose

    ongoing_trip.trip.etas_at_start = etas_at_start
    ongoing_trip.trip.etas = ongoing_trip.trip.etas_at_start

    ongoing_trip.trip.start()
    get_logger(ongoing_trip.sherpa_name).info(f"trip {ongoing_trip.trip_id} started")


def end_trip(
    dbsession: DBSession, ongoing_trip: tm.OngoingTrip, sherpa: fm.Sherpa, success: bool
):

    ongoing_trip.trip.end(success)
    dbsession.delete_ongoing_trip(ongoing_trip)

    # update sherpa status on deleting trip
    sherpa_status: fm.SherpaStatus = sherpa.status
    sherpa_status.idle = True
    sherpa_status.trip_id = None
    sherpa_status.trip_leg_id = None


def start_leg(
    dbsession: DBSession,
    ongoing_trip: tm.OngoingTrip,
    from_station: fm.Station,
    to_station: fm.Station,
) -> tm.TripLeg:

    trip: tm.Trip = ongoing_trip.trip

    from_station_name = from_station.name if from_station else None

    trip_leg: tm.TripLeg = dbsession.create_trip_leg(
        trip.id, from_station_name, to_station.name
    )

    ongoing_trip.start_leg(trip_leg.id)
    sherpa_name = ongoing_trip.sherpa_name

    if from_station:
        update_leg_curr_station(from_station, sherpa_name)

    update_leg_next_station(to_station, sherpa_name)

    return trip_leg


def end_leg(ongoing_trip: tm.OngoingTrip):
    ongoing_trip.trip_leg.end()
    ongoing_trip.end_leg()


def update_leg_curr_station(curr_station: fm.Station, sherpa_name: str):
    curr_station_status = curr_station.status
    if not curr_station_status:
        return
    if sherpa_name in curr_station_status.arriving_sherpas:
        curr_station_status.arriving_sherpas.remove(sherpa_name)


def update_leg_next_station(next_station: fm.Station, sherpa_name: str):
    next_station_status = next_station.status
    if not next_station_status:
        return
    next_station_status.arriving_sherpas.append(sherpa_name)


# checks the status of sherpa(initialized, inducted) and checks if the sherpa is available for a trip
def is_sherpa_available_for_new_trip(sherpa_status):
    AVAILABLE = "available"
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


# FM HEALTH CHECK #
def record_rq_perf():
    redis_conn = redis.from_url(os.getenv("FM_REDIS_URI"))
    fm_backup_path = os.path.join(os.getenv("FM_MAP_DIR"), "data_backup")
    current_data = redis_conn.get("current_data_folder").decode()
    csv_save_path = os.path.join(fm_backup_path, current_data, "rq_perf.csv")

    data = []
    workers = Worker.all(connection=redis_conn)

    column_names = [
        "datetime",
        "worker_name",
        "worker_pid",
        "worker_state",
        "worker_queues",
        "successful_job_count",
        "failed_job_count",
        "total_working_time",
    ]

    for worker in workers:
        worker_data = [
            utils_util.dt_to_str(datetime.datetime.now()),
            worker.name,
            worker.pid,
            worker.state,
            worker.queues,
            worker.successful_job_count,
            worker.failed_job_count,
            worker.total_working_time,
        ]
        data.append(worker_data)

    df = pd.DataFrame(data, columns=column_names)

    header = True if not os.path.exists(csv_save_path) else False
    df.to_csv(csv_save_path, mode="a", index=False, header=header)


def record_cpu_perf():
    ONE_GB = 1024**3

    redis_conn = redis.from_url(os.getenv("FM_REDIS_URI"))
    fm_backup_path = os.path.join(os.getenv("FM_MAP_DIR"), "data_backup")
    current_data = redis_conn.get("current_data_folder").decode()
    csv_save_path = os.path.join(fm_backup_path, current_data, "sys_perf.csv")

    cpu = psutil.cpu_times_percent()
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    net = psutil.net_io_counters()
    cpu_count = psutil.cpu_count()
    load_avg = psutil.getloadavg()
    cpu_freq = psutil.cpu_freq()[0]

    data = [
        [
            utils_util.dt_to_str(datetime.datetime.now()),
            cpu.user,
            cpu.system,
            cpu.idle,
            cpu_count,
            cpu_freq,
            np.round(mem.available / ONE_GB, 3),
            np.round(mem.used / ONE_GB, 3),
            np.round(swap.used / ONE_GB, 3),
            np.round(load_avg[0] * 100 / cpu_count, 1),
            np.round(load_avg[1] * 100 / cpu_count, 1),
            np.round(load_avg[2] * 100 / cpu_count, 1),
            net.packets_sent,
            net.packets_recv,
            net.errin,
            net.errout,
        ]
    ]

    column_names = [
        "datetime",
        "cpu_user",
        "cpu_system",
        "cpu_idle",
        "cpu_count",
        "cpu_freq",
        "mem_available",
        "mem_used",
        "swap_used",
        "load_avg_1",
        "load_avg_5",
        "load_avg_15",
        "net_packets_sent",
        "net_packets_recv",
        "net_errin",
        "net_errout",
    ]

    df = pd.DataFrame(data, columns=column_names)

    header = True if not os.path.exists(csv_save_path) else False
    df.to_csv(csv_save_path, mode="a", index=False, header=header)


def delete_notifications(dbsession: DBSession):
    # at the most only one dispatch notification can be present for a sherpa
    all_notifications = dbsession.get_notifications()

    for notification in all_notifications:
        time_since_notification = datetime.datetime.now() - notification.created_at
        timeout = mm.NotificationTimeout.get(notification.log_level, 120)

        if notification.repetitive:
            timeout = notification.repetition_freq

        if time_since_notification.seconds > timeout:
            # delete any notification which is repetitive and past timeout
            if notification.repetitive:
                dbsession.delete_notification(notification.id)
                continue

            # delete stale alerts caused by dispatch button
            if (
                notification.log_level == mm.NotificationLevels.stale_alert_or_action
                and notification.module == mm.NotificationModules.dispatch_button
            ):
                dbsession.delete_notification(notification.id)
                continue

            if notification.log_level != mm.NotificationLevels.info:
                notification.log_level = mm.NotificationLevels.stale_alert_or_action

            if (
                notification.log_level != mm.NotificationLevels.info
                and len(notification.cleared_by) == 0
            ):
                continue

            dbsession.delete_notification(notification.id)

    # donot allow more pop ups than MAX_NUM_POP_UP_NOTIFICATIONS
    dbsession.make_pop_ups_stale(cc.MAX_NUM_POP_UP_NOTIFICATIONS)


def check_sherpa_status(dbsession: DBSession):
    MULE_HEARTBEAT_INTERVAL = Config.get_fleet_comms_params()["mule_heartbeat_interval"]
    stale_sherpas_status: fm.SherpaStatus = dbsession.get_all_stale_sherpa_status(
        MULE_HEARTBEAT_INTERVAL
    )

    for stale_sherpa_status in stale_sherpas_status:
        if not stale_sherpa_status.disabled:
            stale_sherpa_status.disabled = True
            stale_sherpa_status.disabled_reason = cc.DisabledReason.STALE_HEARTBEAT

        get_logger("status_updates").warning(
            f"stale heartbeat from sherpa {stale_sherpa_status.sherpa_name} last_update_at: {stale_sherpa_status.updated_at} mule_heartbeat_interval: {MULE_HEARTBEAT_INTERVAL}"
        )


def add_sherpa_event(dbsession: DBSession, sherpa_name, msg_type, context):
    dbsession.delete_stale_sherpa_events(sherpa_name)
    sherpa_event: fm.SherpaEvent = fm.SherpaEvent(
        sherpa_name=sherpa_name,
        msg_type=msg_type,
        context="sent by sherpa",
    )
    dbsession.add_to_session(sherpa_event)


# miscellaneous
def get_conveyor_ops_info(trip_metadata):
    get_logger().info(
        f"will parse trip metadata for conveyor ops, Trip metadata: {trip_metadata}"
    )
    num_units = None
    if trip_metadata:
        conveyor_ops = trip_metadata.get("conveyor_ops", None)
        if conveyor_ops:
            num_units = trip_metadata.get("num_units", None)
            if num_units is not None:
                num_units = int(num_units)
    return num_units


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
        map_file_info.append(
            rqm.MapFileInfo(file_name=cert_files[i], hash=all_file_hash[i])
        )

    return map_file_info


def is_reset_fleet_required(fleet_name, map_files):
    fleet_path = os.path.join(os.environ["FM_MAP_DIR"], f"{fleet_name}/map")
    for mf in map_files:
        file_path = f"{fleet_path}/{mf.filename}"
        try:
            filehash = compute_sha1_hash(file_path)
            if filehash != mf.file_hash:
                return True
        except Exception as e:
            get_logger().info(
                f"Unable to find the shasum of file {file_path}, exception: {e}"
            )
            return True
    return False
