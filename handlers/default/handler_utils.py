import logging
import logging.config
import redis
import os
import numpy as np
from typing import List
import datetime
import pandas as pd
from sqlalchemy import func
from sqlalchemy.orm.attributes import flag_modified


# ati code imports
from models.mongo_client import FMMongo
import core.constants as cc
from models.db_session import DBSession
import models.fleet_models as fm
import models.trip_models as tm
import models.misc_models as mm
import utils.util as utils_util
import utils.log_utils as lu


# get log config
logging.config.dictConfig(lu.get_log_config_dict())


# Trip hutils
def assign_sherpa(dbsession: DBSession, trip: tm.Trip, sherpa: fm.Sherpa):
    ongoing_trip = dbsession.create_ongoing_trip(sherpa.name, trip.id)
    trip.assign_sherpa(sherpa.name)
    sherpa_status: fm.SherpaStatus = sherpa.status
    sherpa_status.idle = False
    sherpa_status.trip_id = trip.id
    logging.getLogger(sherpa.name).info(
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
    sherpa_status: fm.SherpaStatus = sherpa.status
    start_pose = sherpa_status.pose
    fleet_name = ongoing_trip.trip.fleet_name

    redis_conn = redis.from_url(os.getenv("FM_REDIS_URI"))
    etas_at_start = []
    route_lengths = []
    start_station_name = None
    for station in all_stations:
        end_pose = station.pose
        end_station_name = station.name
        route_length = utils_util.get_route_length(
            start_pose, end_pose, fleet_name, redis_conn
        )
        if route_length == np.inf:
            start_station_info = (
                start_station_name if start_station_name is not None else start_pose
            )
            reason = f"no route from {start_station_info} to {end_station_name}"
            trip_failed_log = f"{ongoing_trip.sherpa_name} failed to do trip with trip_id: {ongoing_trip.trip.id}) , reason: {reason}"
            logging.getLogger(ongoing_trip.sherpa_name).warning(trip_failed_log)
            dbsession.add_notification(
                [sherpa.name, sherpa.fleet.name, sherpa.fleet.customer],
                trip_failed_log,
                mm.NotificationLevels.alert,
                mm.NotificationModules.errors,
            )
            end_trip(dbsession, ongoing_trip, sherpa, False)
            return

        eta = (
            0
            if route_length == 0
            else dbsession.get_expected_trip_time(start_station_name, end_station_name)
        )
        if eta is None:
            eta = route_length

        route_lengths.append(np.round(route_length, 2))
        etas_at_start.append(np.round(eta, 2))
        start_pose = station.pose
        start_station_name = station.name

    ongoing_trip.trip.route_lengths = route_lengths
    ongoing_trip.trip.etas_at_start = etas_at_start
    ongoing_trip.trip.etas = etas_at_start

    ongoing_trip.trip.start()
    logging.getLogger(ongoing_trip.sherpa_name).info(f"trip {ongoing_trip.trip_id} started")


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
):

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


def end_leg(ongoing_trip: tm.OngoingTrip):
    ongoing_trip.trip_leg.end()
    ongoing_trip.end_leg()
    if ongoing_trip.finished_booked():
        trip_progress = 100
    else:
        trip_progress = np.round(
            (
                np.sum(ongoing_trip.trip.etas_at_start[: ongoing_trip.next_idx_aug])
                / np.sum(ongoing_trip.trip.etas_at_start)
            )
            * 100,
            2,
        )
    ongoing_trip.trip.trip_metadata.update({"total_trip_progress": str(trip_progress)})
    flag_modified(ongoing_trip.trip, "trip_metadata")


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
def record_rq_perf(current_data_folder):
    fm_backup_path = os.path.join(os.getenv("FM_STATIC_DIR"), "data_backup")
    csv_save_path = os.path.join(fm_backup_path, current_data_folder, "rq_perf.csv")
    column_names, data = utils_util.rq_perf()
    data = data
    df = pd.DataFrame(data, columns=column_names)
    header = True if not os.path.exists(csv_save_path) else False
    df.to_csv(csv_save_path, mode="a", index=False, header=header)


def record_cpu_perf(current_data_folder):
    fm_backup_path = os.path.join(os.getenv("FM_STATIC_DIR"), "data_backup")
    csv_save_path = os.path.join(fm_backup_path, current_data_folder, "sys_perf.csv")
    column_names, data = utils_util.sys_perf()
    data = [data]
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

    # clear notification created an hour back
    dt = datetime.datetime.now() + datetime.timedelta(hours=-1)
    dbsession.delete_old_notifications(dt)


def check_sherpa_status(dbsession: DBSession):
    with FMMongo() as fm_mongo:
        comms_config = fm_mongo.get_document_from_fm_config("comms")

    sherpa_heartbeat_interval = comms_config["sherpa_heartbeat_interval"]
    stale_sherpas_status: fm.SherpaStatus = dbsession.get_all_stale_sherpa_status(
        sherpa_heartbeat_interval
    )

    for stale_sherpa_status in stale_sherpas_status:
        sherpa_name = stale_sherpa_status.sherpa_name
        last_sherpa_mode_change = dbsession.get_last_sherpa_mode_change(sherpa_name)

        if not stale_sherpa_status.disabled:
            stale_sherpa_status.disabled = True
            stale_sherpa_status.disabled_reason = cc.DisabledReason.STALE_HEARTBEAT

        logging.getLogger("status_updates").warning(
            f"stale heartbeat from sherpa {stale_sherpa_status.sherpa_name} last_update_at: {stale_sherpa_status.updated_at} mule_heartbeat_interval: {sherpa_heartbeat_interval}"
        )

        if stale_sherpa_status.trip_id:
            utils_util.maybe_add_notification(
                dbsession,
                [
                    stale_sherpa_status.sherpa_name,
                    stale_sherpa_status.sherpa.fleet.name,
                    stale_sherpa_status.sherpa.fleet.customer,
                ],
                f"Lost connection to {stale_sherpa_status.sherpa_name}, sherpa doing trip: {stale_sherpa_status.trip_id}",
                mm.NotificationLevels.alert,
                mm.NotificationModules.errors,
            )

        # set mode change - reflects in sherpa_oee
        disconnected = "disconnected"
        if stale_sherpa_status.mode != disconnected:
            mode = "disconnected"
            stale_sherpa_status.mode = mode
            record_sherpa_mode_change(dbsession, sherpa_name, mode, last_sherpa_mode_change)


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
    logging.getLogger().info(
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


def record_sherpa_mode_change(
    dbsession: DBSession,
    sherpa_name: str,
    mode: str,
    last_sherpa_mode_change: mm.SherpaModeChange,
):

    if last_sherpa_mode_change is not None:
        last_sherpa_mode_change.ended_at = datetime.datetime.now()

    sherpa_mode_change = mm.SherpaModeChange(
        sherpa_name=sherpa_name, mode=mode, started_at=datetime.datetime.now()
    )
    dbsession.add_to_session(sherpa_mode_change)


def update_sherpa_oee(dbsession: DBSession):
    today_now = datetime.datetime.now()
    today_start = today_now.replace(hour=0, minute=0, second=0, microsecond=0)

    sherpa_names = dbsession.get_all_sherpa_names()

    # delete all old entries sherpa mode change entries
    dbsession.session.query(mm.SherpaModeChange).filter(
        mm.SherpaModeChange.ended_at < today_start
    ).delete()

    for sherpa_name in sherpa_names:
        sherpa_oee = dbsession.get_sherpa_oee(sherpa_name, today_start)

        # get mode split up data only for today
        sherpa_mode_split_up = dbsession.get_sherpa_mode_split_up(sherpa_name, today_start)

        temp = (
            dbsession.session.query(mm.SherpaModeChange)
            .filter(mm.SherpaModeChange.sherpa_name == sherpa_name)
            .filter(func.date(mm.SherpaModeChange.ended_at) == today_start.date())
            .filter(func.date(mm.SherpaModeChange.started_at) != today_start.date())
            .one_or_none()
        )

        mode_split_up = {}
        for mode_data in sherpa_mode_split_up:
            mode_time = float(mode_data[1])
            mode_split_up.update({mode_data[0]: mode_time})

        if temp is not None:
            unaccounted_time = (temp.ended_at - today_start).total_seconds()
            if temp.mode in list(mode_split_up.keys()):
                mode_split_up[temp.mode] = mode_split_up[temp.mode] + unaccounted_time
            else:
                mode_split_up.update({temp.mode: unaccounted_time})

        if sherpa_oee is None:
            sherpa_oee = mm.SherpaOEE(sherpa_name=sherpa_name, dt=today_start)
            dbsession.add_to_session(sherpa_oee)

        sherpa_oee.mode_split_up = mode_split_up
        flag_modified(sherpa_oee, "mode_split_up")
