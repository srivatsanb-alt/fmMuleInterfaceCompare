import json
import time
from sqlalchemy import text

from hivemind import models
from hivemind.fleet_manager.analytics import (
    record_conveyor_drop_time,
    record_conveyor_load_time,
    record_status_change,
    record_trip_end,
)
from hivemind.fleet_manager.comms import (
    send_ack_msg,
    send_display_msg_frontend,
    send_fleet_init_msg,
    send_move_to_msg,
    send_msg_to_frontend,
    send_transfer_totes_msg,
    send_ack_to_frontend,
)
from hivemind.fleet_manager.constants import (
    ACTION_COMMAND_MAP,
    HEARTBEAT_CHECK_INTERVAL,
    HEARTBEAT_INTERVAL,
    REROUTE_PROGRESS_THRESHOLD,
    WARMUP_TIME,
    FleetCommands,
    FleetMessages,
)
from hivemind.fleet_manager.dispatcher import (
    check_mule_progress,
    dispatch_mule,
    maybe_send_mule_pose,
    update_conveyor_tote_status,
    update_tote_status_on_dispatch,
    update_tote_status_on_new_totes,
)
from hivemind.fleet_manager.entities import (
    Conveyor,
    Fleet,
    Frontend,
    Mule,
    MuleActions,
)
from hivemind.fleet_manager.fm_utils import (
    add_extra_fields_to_mule_msg,
    are_poses_close,
    send_to_frontend,
    send_to_mule,
)
from hivemind.fleet_manager.globals import name_to_pose
from hivemind.fleet_manager.helpers import (
    change_station_status,
    clear_current_station,
    clear_pickup,
    clear_previous_station,
    disable_entity,
    enable_entity,
    maybe_grant_visa,
    reroute_arriving_mules,
    reroute_mule,
    reset_mule,
    send_chute_status_to_frontend,
    send_mule_to_drop,
    send_mule_to_park_from_chute,
    send_mule_to_park_from_pose,
    send_mule_to_pickupafterdrop,
    send_mule_to_recharge,
    should_forget_msg,
    transfer_totes_mule,
    update_mule_next_dest,
    update_parking_station,
    is_init_msg_valid,
    check_mule_map_files,
    get_values_from_db,
    record_mule_stoppages,
    get_fleet_error_db,
)
from hivemind.core.db import get_db_session
from hivemind.fleet_manager.logs import get_logger
from hivemind.fleet_manager.optimal_dispatch_utils import (
    get_mule_with_max_eta,
    should_dispatch_mule,
    should_send_mule_to_recharge,
)
from hivemind.fleet_manager.redis_utils import FleetRedis, get_redis
from hivemind.fleet_manager.workers import (
    dispatcher_queue,
    enqueue,
    to_frontend_queue,
    to_mule_queue,
)


def add_to_dispatcher_queue(msg):
    enqueue(dispatcher_queue, handle_dispatcher_msgs, msg, at_front=True)


def handle_mule_pickup(all_conveyors_r, mule_r):
    mule_name = mule_r["name"]
    conveyor_r: Conveyor = all_conveyors_r[mule_r["next_dest"]]
    conveyor_r["dispatched_mule"] = mule_name
    mule_r["num_totes_to_transfer"] = min(2, conveyor_r["num_totes"])
    mule_r["is_idle"] = False

    transfer_totes_mule(mule_r, "receive")

    return conveyor_r, mule_r


def handle_mule_drop(mule_r):
    return transfer_totes_mule(mule_r, "send")


def handle_mule_park(mule_r, redis: FleetRedis):
    record_trip_end(mule_r, redis)
    all_waiting_r = redis.get_waiting_totes()
    mule_name = mule_r["name"]

    if should_send_mule_to_recharge(mule_r, redis):
        station_name = mule_r["next_dest"]
        if station_name not in all_waiting_r:
            # station is not a conveyor with totes
            mule_r, _ = send_mule_to_recharge(mule_r, redis)
            get_logger(mule_name).info(f"mule {mule_name} sent for battery swap")
        else:
            get_logger(mule_name).info(
                f"mule {mule_name} not sent for battery swap: {station_name} has waiting totes"
            )

    else:
        mule_r["is_idle"] = True

    return mule_r


def handle_conveyor_started_pickup(mule_r, redis):
    # tell conveyor to start transferring totes to waiting mule.
    conveyor = mule_r["next_dest"]
    num_totes = mule_r["num_totes_to_transfer"]

    send_transfer_totes_msg(conveyor, num_totes)
    get_logger(conveyor).info(
        f"[update] telling conveyor {conveyor} to transfer {num_totes} totes"
    )

    mule_r["last_cmd_sent"] = FleetCommands.TRANSFER_TOTES
    record_conveyor_load_time(mule_r["id"], conveyor, redis)

    return num_totes


def handle_conveyor_completed_drop(
    mule_r, all_mules_r, chute_r, all_conveyors_r, all_parking_r, all_waiting_r, redis
):
    # drop done; send to station for parking
    mule_name = mule_r["name"]
    mule_id = mule_r["id"]

    record_conveyor_drop_time(mule_id, redis)
    record_trip_end(mule_r, redis)

    mule_r["num_totes_to_transfer"] = 0
    if should_send_mule_to_recharge(mule_r, redis):
        next_dest = mule_r["next_trip_dest"]
        if next_dest:
            get_logger(mule_name).info(
                f"mule {mule_name} not sent for battery swap: going to {next_dest}"
            )
        else:
            get_logger(mule_name).info(f"mule {mule_name} sent for battery swap")
            return send_mule_to_recharge(mule_r, redis)

    # need not find a parking if already a pickup was assigned
    if mule_r["next_trip_dest"]:
        mule_r, station = send_mule_to_pickupafterdrop(
            mule_r, chute_r, all_conveyors_r, redis
        )
    else:
        mule_r, station = send_mule_to_park_from_chute(
            mule_r, chute_r, all_conveyors_r, redis
        )

    return mule_r, station


# Handles tote status messages from conveyors.
def handle_tote_status(msg, redis: FleetRedis):
    fleet = msg.get("fleet")
    started = redis.get("fleet_started")
    if not started:
        start_time = redis.get("start_time")
        curr_time = time.time()
        if not start_time:
            start_time = curr_time
            redis.set("start_time", curr_time)
        # wait for fleet to warm up.
        if curr_time - float(start_time) < WARMUP_TIME:
            get_logger(fleet).info("[fleet] Waiting for fleet to warm up")
            return

    conveyor_name = msg["name"]
    if msg["compact_time"] > 0:
        # ignore tote status messages when conveyor is still compacting.
        return

    # data stored in redis.
    all_conveyors_r, all_mules_r, all_parking_r = redis.get_redis_data()
    all_waiting_r = redis.get_waiting_totes()

    conveyor_r: Conveyor = all_conveyors_r[conveyor_name]
    waiting_r = all_waiting_r.get(conveyor_name, None)
    dispatch_mule_r = drop_mule_r = None

    num_totes = msg.get("num_totes", 0)
    num_totes_fulfilled_r = conveyor_r["num_totes_fulfilled"]
    wlen = len(waiting_r["waiting_since"]) if waiting_r else 0
    num_waiting_totes = num_totes - num_totes_fulfilled_r - wlen
    if num_waiting_totes > 0:
        # new totes are waiting at the conveyor.
        conveyor_r, waiting_r = update_tote_status_on_new_totes(
            num_waiting_totes, conveyor_r, waiting_r
        )
        redis.update_waiting_redis(waiting_r, all_waiting_r, conveyor_name)

    dispatch_mule_r = None
    send_mule, reason = should_dispatch_mule(msg, conveyor_r)
    if send_mule:
        # new demand, send mule for pickup.
        get_logger(conveyor_name).info(f"[status] new pickup at {conveyor_name}")
        conveyor_r, dispatch_mule_r, prev_station = dispatch_mule(
            msg, conveyor_r, all_mules_r, all_waiting_r, redis
        )
    elif reason == "prev_mule":
        # new tote will be assigned to previous mule. Do all the necessary updates for this tote.
        update_tote_status_on_dispatch(1, conveyor_r, redis)
        conveyor_r["num_totes_fulfilled"] += 1

    if (
        dispatch_mule_r
        and prev_station != dispatch_mule_r["next_dest"]
        and not dispatch_mule_r["next_trip_dest"]
    ):
        clear_previous_station(dispatch_mule_r, prev_station, redis)

    # update conveyor data to be stored in redis.
    conveyor_r = update_conveyor_tote_status(msg, conveyor_r, dispatch_mule_r, redis)

    all_conveyors_r = redis.get_redis_stations("conveyors")
    redis.update_redis(
        [conveyor_r], [dispatch_mule_r, drop_mule_r], all_conveyors_r, all_mules_r
    )

    if (
        dispatch_mule_r
        and prev_station == dispatch_mule_r["next_dest"]
        and dispatch_mule_r["is_idle"]
    ):
        next_msg = {
            "type": "reached",
            "name": dispatch_mule_r["name"],
            "destination": name_to_pose(redis.fleet_name, prev_station),
            "fleet": dispatch_mule_r["fleet"],
        }
        handle_dispatcher_msgs(next_msg, internal=True)


def handle_correct_reached_destination(msg, redis: FleetRedis):
    mule_name = msg["name"]
    all_conveyors_r, all_mules_r, _ = redis.get_redis_data()
    mule_r: Mule = all_mules_r[mule_name]
    mule_action = mule_r["action"]
    conveyor_r = None

    if mule_action == MuleActions.PARK:
        get_logger(mule_name).info(f"[status] mule {mule_name} reached destination (park)")
        mule_r = handle_mule_park(mule_r, redis)
    elif mule_action == MuleActions.PICKUP:
        get_logger(mule_name).info(
            f"[status] mule {mule_name} reached destination (pickup)"
        )
        conveyor_r, mule_r = handle_mule_pickup(all_conveyors_r, mule_r)
    elif mule_action == MuleActions.DROP:
        get_logger(mule_name).info(f"[status] mule {mule_name} reached destination (drop)")
        handle_mule_drop(mule_r)
    elif mule_action == MuleActions.RECHARGE:
        get_logger(mule_name).info(
            f"[status] mule {mule_name} reached destination (recharge)"
        )
        redis.srem("mules_to_recharge", mule_name)
    else:
        get_logger(mule_name).error(f"Invalid action {mule_action} by mule {mule_name}")
        raise ValueError(f"Invalid action {mule_action} by mule {mule_name}")

    return conveyor_r, mule_r


# Handles trip completion messages from mules.
def handle_reached_destination(msg, redis: FleetRedis, internal=False):
    mule_name = msg["name"]
    dest_pose = msg["destination"]

    all_conveyors_r, all_mules_r, _ = redis.get_redis_data()

    conveyor_r = None
    mule_r: Mule = all_mules_r[mule_name]
    reached_pose = mule_r["reached_pose"]
    next_pose = mule_r["next_pose"]
    current_pose = mule_r["current_pose"]

    if next_pose and not are_poses_close(next_pose, current_pose, mule_name):
        # mule did not reach where we sent it. Send another move command.
        get_logger(mule_name).info(
            f"[status] mule {mule_name} at {current_pose} (kidnapped)"
        )
        get_logger(mule_name).info(
            f"[update] telling mule {mule_name} to move to {next_pose}"
        )
        send_move_to_msg(mule_r, next_pose, redis)

        mule_r["is_idle"] = False
        # Derive move-to command from mule action.
        mule_r["last_cmd_sent"] = ACTION_COMMAND_MAP[mule_r["action"]]
    elif (
        not internal
        and reached_pose
        and are_poses_close(reached_pose, dest_pose, mule_name)
    ):
        # sometimes mules send multiple reached destinations with
        # small change in poses. Ignore the second message.
        get_logger(mule_name).info(
            f"[status] mule {mule_name} prev pose {reached_pose}, curr pose {dest_pose}, ignoring latest message"
        )
        return False
    else:
        c_r, m_r = handle_correct_reached_destination(msg, redis)
        # overwrite only if not null
        conveyor_r = c_r if c_r else conveyor_r
        mule_r = m_r if m_r else mule_r

    if mule_r["action"] == MuleActions.PARK and conveyor_r:
        conveyor_r["parked_mule"] = mule_r["name"]

    mule_r["reached_pose"] = dest_pose
    redis.update_redis([conveyor_r], [mule_r], all_conveyors_r, all_mules_r)
    return True


# Handles conveyor completed messages from mules. If the mule is at a pickup station,
# tells pickup conveyor to transfer. If the mule is at a drop chute, tells mule to go
# to parking.
def handle_conveyor_completed(msg, redis: FleetRedis):
    mule_name = msg["name"]
    num_totes = msg["totes_moved"]
    fleet = msg["fleet"]

    all_conveyors_r, all_mules_r, all_parking_r = redis.get_redis_data()
    all_waiting_r = redis.get_waiting_totes()

    mule_r: Mule = all_mules_r[mule_name]
    mule_id = mule_r["id"]
    mule_action = mule_r["action"]

    conveyor_r = None

    if mule_action == MuleActions.PICKUP:
        get_logger(mule_name).info(f"[status] mule {mule_name} conveyor completed (pickup)")
        conveyor_name = mule_r["next_dest"]
        conveyor_r = all_conveyors_r[conveyor_name]
        record_conveyor_load_time(mule_id, conveyor_name, redis)
        record_trip_end(mule_r, redis)

        conveyor_r, mule_r = send_mule_to_drop(conveyor_r, mule_r, redis)
        conveyor_r["num_totes_fulfilled"] -= num_totes
        get_logger(conveyor_name).info(
            f"[update] conveyor {conveyor_name} pickup completed, num_totes_fulfilled decreased by {num_totes}"
        )
        #   handle_conveyor_completed_pickup(mule_r)
        total_totes = mule_r.get("total_totes", 0)
        mule_r["total_totes"] = total_totes + num_totes
    elif mule_action == MuleActions.DROP:
        get_logger(mule_name).info(f"[status] mule {mule_name} conveyor completed (drop)")
        chute_name = mule_r["next_dest"]
        chute_r = redis.get_redis_chute(chute_name)
        chute_total_totes = chute_r["total_totes"]
        chute_total_totes += num_totes
        chute_r["total_totes"] = chute_total_totes
        redis.set_redis_chute(chute_name, chute_r)
        get_logger(fleet).info(f"chute {chute_name} : num_totes {chute_total_totes}")
        send_chute_status_to_frontend(chute_name, chute_r)
        mule_r, station = handle_conveyor_completed_drop(
            mule_r,
            all_mules_r,
            chute_r,
            all_conveyors_r,
            all_parking_r,
            all_waiting_r,
            redis,
        )
        update_parking_station(station, redis)
    else:
        get_logger(fleet).error(f"invalid mule action: {mule_action}")
        get_logger(mule_name).error(f"invalid mule action: {mule_action}")
        raise ValueError("Invalid mule action")

    redis.update_redis([conveyor_r], [mule_r], all_conveyors_r, all_mules_r)


def handle_conveyor_started(msg, redis: FleetRedis):
    mule_name = msg["name"]

    all_conveyors_r, all_mules_r, all_parking_r = redis.get_redis_data()

    mule_r: Mule = all_mules_r[mule_name]
    mule_id = mule_r["id"]
    mule_action = mule_r["action"]

    if mule_action == MuleActions.PICKUP:
        get_logger(mule_name).info(f"mule {mule_name} conveyor started (pickup)")
        handle_conveyor_started_pickup(mule_r, redis)
    elif mule_action == MuleActions.DROP:
        get_logger(mule_name).info(f"mule {mule_name} conveyor started (drop)")
        record_conveyor_drop_time(mule_id, redis)

    else:
        get_logger(mule_name).error(f"mule {mule_name} invalid action: {mule_action}")
        return

    redis.update_redis([], [mule_r], None, all_mules_r)


def handle_visa_request(msg, redis: FleetRedis):
    all_conveyors_r, all_mules_r, all_parking_r = redis.get_redis_data()
    mule_name = msg["name"]
    zone_id = str(msg["zone_id"])
    visa_type = msg["visa_type"]

    mule_r = all_mules_r[mule_name]

    granted, visa_str, other_zone_id = maybe_grant_visa(
        mule_name, zone_id, visa_type, redis
    )
    if other_zone_id is not None and other_zone_id != zone_id:
        # release other visa and try again.
        get_logger(mule_name).info(
            f"clearing locks held by mule {mule_name} and retrying visa grant"
        )
        redis.clear_exclusion_zone_locks(mule_name)
        granted, visa_str, _ = maybe_grant_visa(mule_name, zone_id, visa_type, redis)

    granted_message = "granted" if granted else "not granted"
    get_logger(mule_name).info(
        f"[status] {mule_name} mule requested for {visa_type} visa to zone {zone_id}: {granted_message}"
    )

    to_mule_command = {
        "mule": mule_name,
        "action": "visa_granted",
        "granted": granted,
        "zone_id": zone_id,
        "visa_type": visa_type,
    }
    mule_r["previous_visa_status"] = mule_r.get("latest_visa_status", "")
    mule_r["latest_visa_status"] = visa_str

    redis.update_redis([], [mule_r], all_conveyors_r, all_mules_r)
    enqueue(to_mule_queue, send_to_mule, to_mule_command)


def handle_visa_release(msg, redis: FleetRedis):
    all_conveyors_r, all_mules_r, all_parking_r = redis.get_redis_data()
    mule_name = msg["name"]
    zone_id = str(msg["zone_id"])
    visa_type = msg["visa_type"]

    mule_r = all_mules_r[mule_name]
    visa_str = ""
    if visa_type == "unparking":
        redis.unlock_exclusion_zone(zone_id + "_station", mule_name)
        redis.unlock_exclusion_zone(zone_id + "_lane", mule_name)
        visa_str = f"unparking: Unlocked {zone_id}_station and {zone_id}_lane"
    elif visa_type == "transit":
        redis.unlock_exclusion_zone(zone_id + "_lane", mule_name, exclusive=False)
        visa_str = f"transit: Unlocked {zone_id}_lane"

    if (visa_type in ("unparking", "transit")) and (
        redis.hget("exclusion_zones_held", mule_name) == zone_id
    ):
        redis.hdel("exclusion_zones_held", mule_name)

    get_logger(mule_name).info(
        f"[status] {mule_name} mule released {visa_type} visa to zone {zone_id}"
    )

    to_mule_command = {
        "mule": mule_name,
        "action": "visa_released",
        "zone_id": zone_id,
        "visa_type": visa_type,
    }
    mule_r["previous_visa_status"] = mule_r.get("latest_visa_status", "")
    mule_r["latest_visa_status"] = visa_str
    redis.update_redis([], [mule_r], all_conveyors_r, all_mules_r)
    enqueue(to_mule_queue, send_to_mule, to_mule_command)


def handle_trip_status(msg, redis: FleetRedis):
    pose = msg["current_pose"]
    mule_name = msg["name"]
    fleet = msg["fleet"]

    frontend_r: Frontend = redis.get_redis_frontend()
    if not frontend_r:
        frontend_r = Frontend().__dict__
        redis.set("frontend", json.dumps(frontend_r))

    all_mules_r = redis.get_redis_mules()
    all_conveyors_r = redis.get_redis_conveyors()
    all_chutes_r = redis.get_redis_stations("chutes")
    all_parking_r = redis.get_redis_stations("parking")
    parking_only_conveyors = redis.get_any_entity("parking_only_conveyors")

    mule_r = all_mules_r[mule_name]

    mule_r["current_pose"] = pose
    mule_r["trip_ts"] = time.time()
    mule_r["trip_eta"] = msg["eta"]
    all_mules_r[mule_r["name"]] = mule_r
    redis.update_entity(all_mules_r, "mules")

    destination = mule_r["next_dest"]
    all_stations_r = None
    station_type = None

    if destination:
        if destination in all_chutes_r:
            all_stations_r = all_chutes_r
            station_type = "chutes"
        elif destination in all_conveyors_r:
            all_stations_r = all_conveyors_r
            station_type = "conveyors"
        elif destination in all_parking_r:
            all_stations_r = all_parking_r
            station_type = "parking"

        if all_stations_r:
            arriving_mules = all_stations_r[destination]["arriving_mules"]
            if len(arriving_mules) > 1:
                max_eta, last_arriving_mule = get_mule_with_max_eta(
                    all_mules_r, arriving_mules
                )
            else:
                max_eta = mule_r["trip_eta"]
                last_arriving_mule = mule_r["name"]
            if last_arriving_mule == mule_r["name"] and max_eta is not None:
                station_updated = all_stations_r[destination]
                station_updated["trip_ts"] = time.time()
                station_updated["trip_eta"] = max_eta
                all_stations_r[destination] = station_updated
                redis.update_entity(all_stations_r, station_type)

    if not mule_r["is_idle"]:
        mule_r = check_mule_progress(msg, mule_r, redis)
        if not msg["velocity_speed_factor"]:
            stop_reason = f"{mule_name} stopped, reason unknown"
            reason = "unknown"
            if msg["obstacle_speed_factor"] == 0 and msg["local_obstacle"]:
                obst_pose = msg["local_obstacle"]
                x_dir = "right" if (obst_pose[0] > 0) else "left"
                y_dir = "ahead" if (obst_pose[1] > 0) else "behind"
                stop_reason = f"{mule_name} stopped due to an obstacle {abs(obst_pose[0])} m to the {x_dir} and {abs(obst_pose[1])} m {y_dir}"
                reason = "obstacle"
            if msg["visa_speed_factor"] < 1:
                stop_reason = f"{mule_name} stopped, visa not granted"
                reason = "visa"
            send_display_msg_frontend("mule", mule_name, stop_reason, redis.fleet_name)
            record_mule_stoppages(msg, mule_r, reason, redis)

    if destination and all_stations_r and msg["progress"]:
        destination_r = all_stations_r[destination]
        is_exception = False
        if mule_r["action"] == MuleActions.PARK and destination in parking_only_conveyors:
            is_exception = True
        if (
            msg["progress"] > REROUTE_PROGRESS_THRESHOLD
            and destination_r["is_disabled"]
            and not is_exception
        ):
            reroute_mule(mule_r["name"], redis)
            all_mules_r = redis.get_any_entity("mules")
            mule_r = all_mules_r[mule_name]

    frontend_r = maybe_send_mule_pose(frontend_r, all_mules_r, redis.fleet_name)
    redis.update_redis_frontend(frontend_r)

    shutdown_mules_r = []
    pickup_conveyors_r = []
    curr_time = time.time()
    redis.hset("last_heartbeat", mule_name, curr_time)

    ts = msg["timestamp"]
    msg_latency = curr_time - ts
    if msg_latency > 5:
        get_logger(mule_name).warn(f"heartbeat received after {msg_latency} seconds")
    last_timepoint = redis.hget("last_heartbeat_timepoint", mule_name)
    if not last_timepoint:
        redis.hset("num_heartbeats_last_sec", mule_name, 0)
        redis.hset("heartbeat_latency_last_sec", mule_name, 0)
        redis.hset("last_heartbeat_timepoint", mule_name, curr_time)
    elif curr_time - float(last_timepoint) > 1:
        num_heartbeats_last_sec = int(redis.hget("num_heartbeats_last_sec", mule_name))
        latency = float(redis.hget("heartbeat_latency_last_sec", mule_name))
        if num_heartbeats_last_sec > 0:
            get_logger(mule_name).debug(
                f"avg heartbeat latency last sec: {latency / num_heartbeats_last_sec}"
            )
        redis.hset("num_heartbeats_last_sec", mule_name, 0)
        redis.hset("heartbeat_latency_last_sec", mule_name, 0)
        redis.hset("last_heartbeat_timepoint", mule_name, curr_time)
    redis.hincrby("num_heartbeats_last_sec", mule_name, 1)
    redis.hincrbyfloat("heartbeat_latency_last_sec", mule_name, msg_latency)

    # check for shutdown mules.
    last_heartbeat_check = redis.get("last_heartbeat_check")
    if (
        not last_heartbeat_check
        or curr_time - float(last_heartbeat_check) > HEARTBEAT_CHECK_INTERVAL
    ):
        get_logger(fleet).debug("Checking for heartbeat of all mules")
        heartbeat_times = redis.hgetall("last_heartbeat")
        for mule_name, hbeat_time in heartbeat_times.items():
            shutdown_mule_r = all_mules_r[mule_name]
            if not shutdown_mule_r["initialized"]:
                continue
            if curr_time - float(hbeat_time) > HEARTBEAT_INTERVAL:
                get_logger(mule_name).warn(
                    f"No heartbeat from mule {mule_name} for {HEARTBEAT_INTERVAL} seconds, disabling..."
                )
                shutdown_mule_r, pickup_conveyor_r = handle_mule_shutdown(
                    shutdown_mule_r, redis, "no heartbeat"
                )
                shutdown_mules_r.append(shutdown_mule_r)
                pickup_conveyors_r.append(pickup_conveyor_r)
        redis.set("last_heartbeat_check", curr_time)

    mule_list = [mule_r]
    mule_list.extend(shutdown_mules_r)
    redis.update_redis(pickup_conveyors_r, mule_list, all_conveyors_r, all_mules_r)

    if all_stations_r:
        all_stations_r = redis.get_any_entity(station_type)
        station_pose = all_stations_r[destination]["pose"]
        if (
            all_stations_r[destination]["parked_mule"]
            and all_stations_r[destination]["parked_mule"] != mule_name
            and mule_r["action"] == MuleActions.PICKUP
            and (not mule_r["is_disabled"])
            and (not are_poses_close(mule_r["current_pose"], station_pose, mule_r["name"]))
        ):
            clear_pickup(mule_r, redis)


def handle_change_station_status(msg, redis: FleetRedis):
    station_name = msg["station_name"]
    station_type = msg["station_type"]
    status = msg["status"]
    disable_valid = change_station_status(station_name, station_type, status, redis)
    if disable_valid:
        change = "enabled" if status else "disabled"
        record_status_change(station_name, station_type, change, "user request")
    if disable_valid and not status and station_type == "chute":
        all_chutes_r = redis.get_redis_stations("chutes")
        reroute_arriving_mules(station_name, all_chutes_r, redis)


def handle_invalid_init(msg, reasons, redis):
    mule_name = msg["name"]
    display_name = msg["display_name"]
    api_key = msg["api_key"]
    mule_api_keys = redis.get_any_entity("mule_api_keys")

    if "chassis_api_mismatch" in reasons:
        get_logger(redis.fleet_name).info(
            f"chassis api mismatch, cannot continue mule init for {display_name}"
        )
        display_msg = f"chassis_api_mismatch {mule_name} ({display_name})"
        send_display_msg_frontend("mule", mule_name, display_msg, redis.fleet_name)

    if "api_duplication" in reasons:
        other_mule_name = mule_api_keys[api_key]["mule_name"]
        other_display_name = mule_api_keys[api_key]["display_name"]
        get_logger(redis.fleet_name).info(
            f"api key duplication, cannot continue mule init for {display_name}, ({display_name}) has the same api key as {other_mule_name}-{other_display_name}"
        )
        display_msg = f"api key duplication {mule_name} ({display_name}) has the same upi key as {other_mule_name}-{other_display_name}"
        send_display_msg_frontend("mule", mule_name, display_msg, redis.fleet_name)

    if "invalid_map_files" in reasons:
        get_logger(redis.fleet_name).info(
            f"{display_name} is refering to invalid map files, cannot continue mule init for {display_name}"
        )
        display_msg = f"{mule_name}({display_name}) is refering to invalid map files, cannot continue with init"
        send_display_msg_frontend("mule", mule_name, display_msg, redis.fleet_name)

    if "invalid_fleet_name" in reasons:
        get_logger(redis.fleet_name).info(
            f"{display_name} is refering to invalid fleet_name, cannot continue mule init for {display_name}"
        )
        display_msg = f"{mule_name}({display_name}) is refering to invalid fleet_name, cannot continue with init"
        send_display_msg_frontend("mule", mule_name, display_msg, redis.fleet_name)

    to_mule_msg = {
        "mule": mule_name,
        "display_name": display_name,
        "action": "invalid_init_msg",
        "reasons": reasons,
    }
    enqueue(to_mule_queue, send_to_mule, to_mule_msg)


def handle_mule_init(msg, redis: FleetRedis):
    mule_name = msg["name"]
    curr_pose = msg.get("current_pose")
    display_name = msg["display_name"]
    mule_address = msg["mule_address"]
    api_key = msg["api_key"]
    chassis_number = msg["chassis_number"]
    fleet = msg["fleet"]
    mule_api_keys = redis.get_any_entity("mule_api_keys")
    init_valid, reasons = is_init_msg_valid(msg, redis)
    auto_update_map = msg.get("auto_update_map", True)

    if not auto_update_map and "invalid_map_files" in reasons and len(reasons) == 1:

        display_msg = (
            f"{mule_name} will operate with an experimental map, auto_update_map: False"
        )
        send_display_msg_frontend("mule", mule_name, display_msg, redis.fleet_name)
        get_logger(mule_name).info(
            f"{mule_name} will operate with an experimental map, auto_update_map: False"
        )
        init_valid = True
        reasons = []

    if init_valid:
        mule_api_keys.update(
            {
                api_key: {
                    "mule_name": mule_name,
                    "display_name": display_name,
                    "chassis_number": chassis_number,
                }
            }
        )
        redis.update_entity(mule_api_keys, "mule_api_keys")
        all_mules_r = redis.get_redis_mules()
        all_conveyors_r = redis.get_redis_conveyors()
        mule_r = all_mules_r[mule_name]
        conveyor_r = None

        # get pose from message if provided else get stored value.
        pose = curr_pose if curr_pose else mule_r["current_pose"]
        mule_r, conveyor_r = _handle_mule_init(mule_r, msg, pose, redis)
        mule_r["display_name"] = display_name
        mule_r["ip"] = mule_address
        mule_r["fleet"] = fleet
        mule_r["initialized"] = True

        get_logger(mule_name).info(f"[update] mule {mule_name} initialized")
        if mule_r["action"] == MuleActions.RECHARGE:
            # mule is done with battery swap and should be sent to park.
            mule_r, _ = send_mule_to_park_from_pose(mule_r, redis)
        redis.update_redis([conveyor_r], [mule_r], all_conveyors_r, all_mules_r)
        # treat an init as a heartbeat to avoid mules being shutdown on sending their first
        # trip_status of the day.
        redis.hset("last_heartbeat", mule_name, time.time())
    else:
        all_mules_r = redis.get_redis_mules()
        mule_r = all_mules_r[mule_name]
        mule_r["initialized"] = False
        redis.update_redis_mule(mule_r)
        handle_invalid_init(msg, reasons, redis)
        if auto_update_map and "invalid_map_files" in reasons:
            update_map_msg = {"type": "update_mule_map", "mule_name": mule_r["name"]}
            handle_update_mule_map(update_map_msg, redis)


def _handle_mule_init(mule_r, msg, pose, redis: FleetRedis):
    mule_name = mule_r["name"]
    reset = msg.get("complete_reset")
    last_hbeat = redis.hget("last_heartbeat", mule_name)

    # do a complete reset if asked or if last heartbeat was a long time ago.
    complete_reset = reset or (
        last_hbeat and time.time() - float(last_hbeat) > HEARTBEAT_INTERVAL
    )

    fleet_r = Fleet.from_json(redis.get("fleet"))
    if complete_reset or mule_name in fleet_r.mules_init_sent:
        # only reset if a complete reset is needed or if we restarted and requested an init
        # from mule.
        get_logger(mule_name).info(
            f"resetting mule {mule_name}, complete_reset={complete_reset}"
        )
        mule_r = reset_mule(mule_r, msg, pose, redis, complete_reset)

    # clear reached_pose as we may send an internal reached destination.
    mule_r["reached_pose"] = []

    get_logger(mule_name).info(f"[update] trying to recover mule {mule_name}")
    conveyor_r = handle_mule_recovery(mule_r, pose, redis)
    return mule_r, conveyor_r


def handle_conveyor_error(msg, redis: FleetRedis):
    mule_name = msg["name"]
    wait_for_user_action = True
    action = None
    # errors common to pickup/drop
    if msg["tote_stuck"]:
        issue = "tote_stuck"
        wait_for_user_action = True
    elif msg["tote_count_mismatch"]:
        issue = "tote_count_mismatch"
        wait_for_user_action = True
    elif msg["error_flag"]:
        issue = "error on mule side"
        wait_for_user_action = False

    all_mules_r = redis.get_any_entity("mules")
    mule_r = all_mules_r[mule_name]
    station_name = mule_r["next_dest"]
    error_type = FleetMessages.CONV_ERROR

    if mule_r["action"] == MuleActions.PICKUP:
        clear_pickup(mule_r, redis)
        action = "pickup"
        station_type = "conveyor"
        if msg["tote_overload"]:
            issue = "tote overload"
            wait_for_user_action = True
        get_logger(station_name).info(
            f"{error_type}: {action} not completed by {mule_name} at {station_name}, reason: {issue}"
        )

    elif mule_r["action"] == MuleActions.DROP:
        if mule_r["next_trip_dest"]:
            clear_pickup(mule_r, redis)
        action = "drop"
        station_type = "chute"
        get_logger().info(
            f"{error_type}: {action} not completed by {mule_name} at {station_name}, reason: {issue}"
        )

    all_mules_r = redis.get_any_entity("mules")
    mule_r = all_mules_r[mule_name]
    mule_r["is_idle"] = True
    mule_r["issue"] = issue
    redis.update_entity(all_mules_r, "mules")

    get_logger(mule_name).info(
        f"{error_type}: {action} not completed by {mule_name} at {station_name}, reason: {issue}"
    )

    db = get_db_session()
    result = None
    num_errors = len(db.query(models.FleetErrors).all())
    if num_errors:
        info = text(
            """select max(error_id) from fleet_errors;
            """
        )
        result = db.execute(info)
        for row in result:
            result = row[0]

    error_id = 1 if (not result) else (result + 1)
    get_logger(redis.fleet_name).info(
        f"storing {issue} issue with {mule_name}, {station_name} in db, error_id {error_id}"
    )

    db_error = models.FleetErrors(
        error_id=error_id,
        station=station_name,
        mule=mule_name,
        error_type=error_type,
        issue=issue,
        action=action,
        fleet_name=redis.fleet_name,
    )
    db.add(db_error)
    db.commit()

    new_msg = {
        "type": error_type,
        "action": action,
        "entity_type": station_type,
        "entity_name": station_name,
        "issue": issue,
        "error_id": error_id,
        "fleet": redis.fleet_name,
    }
    enqueue(to_frontend_queue, send_to_frontend, new_msg)
    new_msg = {
        "type": error_type,
        "action": action,
        "entity_type": "mule",
        "entity_name": mule_r["name"],
        "issue": issue,
        "error_id": error_id,
        "fleet": redis.fleet_name,
    }
    enqueue(to_frontend_queue, send_to_frontend, new_msg)
    display_msg = f"resolve {issue} at {mule_name}, {station_name} and resume operation"
    send_display_msg_frontend(station_type, station_name, display_msg, redis.fleet_name)
    send_display_msg_frontend("mule", mule_name, display_msg, redis.fleet_name)
    handle_any_error(mule_r["name"], "mule", issue, redis, wait_for_user_action)
    handle_any_error(station_name, station_type, issue, redis, wait_for_user_action)


def handle_any_error(
    entity_name, entity_type, issue, redis: FleetRedis, wait_for_user_action
):
    if not wait_for_user_action and entity_type == "mule":
        all_mules_r = redis.get_any_entity("mules")
        mule_r = all_mules_r[entity_name]
        mule_r, _ = handle_mule_shutdown(mule_r, redis, issue)
        all_mules_r[entity_name] = mule_r
        redis.update_entity(all_mules_r, "mules")
    else:
        disable_entity(entity_name, entity_type, redis, issue)


def handle_tote_reset_ack(msg, redis: FleetRedis):
    prev_task = msg["prev_task"]
    mule_name = msg["name"]
    all_mules_r = redis.get_any_entity("mules")
    mule_r = all_mules_r[mule_name]
    if not mule_r["is_disabled"]:
        return
    if prev_task == "drop":
        new_msg = {
            "type": "conveyor",
            "name": mule_name,
            "totes_moved": mule_r["num_totes_to_transfer"],
            "fleet": redis.fleet_name,
        }
        handle_conveyor_completed(new_msg, redis)
    enable_entity(mule_name, "mule", redis, "tote reset ack")


def handle_issue_status(msg, redis: FleetRedis):
    issue_type = msg["issue_type"]
    resolved = msg["resolved"]
    entity_type = msg["entity_type"]
    entity_name = msg["entity_name"]

    # send ack to UI
    send_ack_to_frontend(msg)

    if resolved:
        if issue_type == FleetMessages.CONV_ERROR:
            db = get_db_session()
            db_fleet_error = get_values_from_db(
                db, "fleet_errors", "error_id", msg["error_id"]
            )[0]
            station_name = db_fleet_error.station
            station_type = "conveyor" if db_fleet_error.action == "pickup" else "chute"

            action = msg["action"]
            tote_reset_msg = {
                "mule": db_fleet_error.mule,
                "type": FleetCommands.RESET_TOTES,
                "action": "reset",
                "complete_reset": False,
                "prev_task": action,
                "fleet": redis.fleet_name,
            }
            enqueue(to_mule_queue, send_to_mule, tote_reset_msg)
            mule_r = redis.get_redis_mules()[db_fleet_error.mule]
            mule_r["last_cmd_sent"] = FleetCommands.RESET_TOTES
            redis.update_redis_mule(mule_r)

            mule_resolve_msg = msg.copy()
            msg["type"] = "issue_status"
            mule_resolve_msg["entity_name"] = db_fleet_error.mule
            mule_resolve_msg["entity_type"] = "mule"

            send_ack_to_frontend(mule_resolve_msg)

            # hack for one click resolve
            station_resolve_msg = msg.copy()
            msg["type"] = "issue_status"
            station_resolve_msg["entity_name"] = db_fleet_error.station
            station_resolve_msg["entity_type"] = station_type
            send_ack_to_frontend(station_resolve_msg)

            enable_entity(station_name, station_type, redis, issue_type + " resolved")
            all_mules_r = redis.get_any_entity("mules")
            mule_r = all_mules_r[db_fleet_error.mule]
            mule_r["issue"] = None
            redis.update_entity(all_mules_r, "mules")

            db.query(models.FleetErrors).filter_by(error_id=msg["error_id"]).delete()
            db.commit()

            # delete all fleet error entries belonging to the station and the mule
            try:
                db.query(models.FleetErrors).filter_by(
                    station=db_fleet_error.station
                ).delete()
                db.commit()
            except:
                pass
            try:
                db.query(models.FleetErrors).filter_by(mule=db_fleet_error.mule).delete()
                db.commit()
            except:
                pass

        if entity_type == "mule":
            all_mules_r = redis.get_any_entity("mules")
            mule_r = all_mules_r[entity_name]
            mule_r["issue"] = None
            redis.update_entity(all_mules_r, "mules")

        elif entity_type in ["chute", "conveyor"]:
            enable_entity(entity_name, entity_type, redis, issue_type + " resolved")
    else:
        if entity_type == "mule":
            all_mules_r = redis.get_any_entity("mules")
            mule_r = all_mules_r[entity_name]
            mule_r, _ = handle_mule_shutdown(mule_r, redis, issue_type + " not resolved")
            all_mules_r[entity_name] = mule_r
            redis.update_entity(all_mules_r, "mules")


def handle_change_mule_status(msg, redis: FleetRedis):
    mule_name = msg["mule_name"]
    status = True if msg["command"] == "enable" else False

    if status:
        enable_entity(mule_name, "mule", redis, "user request")
    else:
        display_msg = "mules cannot be disabled on user request"
        send_display_msg_frontend("mule", mule_name, display_msg, redis.fleet_name)

    # ack message to UI
    send_ack_to_frontend(msg)


def handle_mule_shutdown(mule_r, redis: FleetRedis, reason=None):
    mule_name = mule_r["name"]
    get_logger(mule_name).info(f"[update] shutting down mule {mule_name}")
    conveyor_r = None
    mule_r["initialized"] = False
    clear_current_station(mule_r, redis)
    redis.clear_exclusion_zone_locks(mule_name)

    next_dest = mule_r["next_dest"]
    if next_dest:
        msg_content = f"current trip to {next_dest} by {mule_name} will not be completed after {mule_name} boots up again"
        send_display_msg_frontend("mule", mule_name, msg_content, redis.fleet_name)

    record_status_change(mule_name, "mule", "shutdown", reason)

    # remove api key from redis on mule shutdwon
    mule_api_keys = redis.get_any_entity("mule_api_keys")
    for api_key, mules in mule_api_keys.items():
        if mule_api_keys[api_key]["mule_name"] == mule_name:
            del mule_api_keys[api_key]
            redis.update_entity(mule_api_keys, "mule_api_keys")
            break

    return mule_r, conveyor_r


def handle_battery_status(msg, redis: FleetRedis):
    mule_name = msg["name"]
    all_mules_r = redis.get_redis_mules()
    all_conveyors_r, all_mules_r, _ = redis.get_redis_data()
    mule_r = all_mules_r[mule_name]
    mule_r["battery_status"] = msg["battery_percentage"]
    redis.update_redis([], [mule_r], all_conveyors_r, all_mules_r)


def handle_battery_swap(msg, redis: FleetRedis):
    all_mules_r = redis.get_redis_mules()
    send_ack_to_frontend(msg)
    for mule_name, mule_r in all_mules_r.items():
        redis.sadd("mules_to_recharge", mule_name)
        if mule_r["action"] == MuleActions.PARK:
            get_logger(mule_name).info(
                f"mule {mule_name} in state park, sent for battery swap"
            )
            send_mule_to_recharge(mule_r, redis)


def handle_mule_battery_swap(msg, redis: FleetRedis):
    send_ack_to_frontend(msg)
    mule_name = msg["mule_name"]
    redis.sadd("mules_to_recharge", mule_name)
    all_mules_r = redis.get_redis_mules()
    mule_r = all_mules_r[mule_name]
    if mule_r["action"] == MuleActions.PARK:
        get_logger(mule_name).info(f"mule {mule_name} in state park, sent for battery swap")
        mule_r, _ = send_mule_to_recharge(mule_r, redis)
        all_mules_r[mule_name] = mule_r
        redis.update_entity(all_mules_r, "mules")


def handle_fleet_status_request(msg, redis: FleetRedis):
    fleet = msg["fleet"]
    entity_type = msg["entity_type"]
    statuses = []

    fleet_status = redis.get_any_entity("fleet_status")
    mule_emergency_stop_dict = redis.get_any_entity("mule_emergency_stop_dict")

    if entity_type == "conveyors" or entity_type == "all":
        conveyors_r = redis.get_redis_conveyors()
        chutes_r = redis.get_any_entity("chutes")
        statuses.extend(
            [
                {
                    "name": name,
                    "type": "conveyor",
                    "num_totes": c["num_totes"],
                    "is_disabled": c["is_disabled"],
                    "issue": None
                    if not get_fleet_error_db(name, "conveyor")
                    else get_fleet_error_db(name, "conveyor")[5],
                    "issue_type": None
                    if not get_fleet_error_db(name, "conveyor")
                    else get_fleet_error_db(name, "conveyor")[2],
                    "error_id": None
                    if not get_fleet_error_db(name, "conveyor")
                    else get_fleet_error_db(name, "conveyor")[1],
                    "action": "pickup",
                }
                for name, c in conveyors_r.items()
            ]
        )

    if entity_type == "chutes" or entity_type == "all":
        statuses.extend(
            [
                {
                    "name": name,
                    "type": "chute",
                    "is_disabled": c["is_disabled"],
                    "issue": None
                    if not get_fleet_error_db(name, "chute")
                    else get_fleet_error_db(name, "chute")[5],
                    "error_id": None
                    if not get_fleet_error_db(name, "chute")
                    else get_fleet_error_db(name, "chute")[1],
                    "action": "drop",
                }
                for name, c in chutes_r.items()
            ]
        )
    if entity_type == "mules" or entity_type == "all":
        mules_r = redis.get_redis_mules()
        statuses.extend(
            [
                {
                    "name": name,
                    "type": "mule",
                    "action": MuleActions.to_str(m["action"]),
                    "num_totes": m["num_totes_to_transfer"],
                    "is_disabled": False if not get_fleet_error_db(name, "mule") else True,
                    "in_error": False if not get_fleet_error_db(name, "mule") else True,
                    "initialized": m.get("initialized", False),
                    "issue": None
                    if not get_fleet_error_db(name, "mule")
                    else get_fleet_error_db(name, "mule")[5],
                    "dest": m.get("next_dest", ""),
                    "error_id": None
                    if not get_fleet_error_db(name, "mule")
                    else get_fleet_error_db(name, "mule")[1],
                    "emergency_stop": mule_emergency_stop_dict.get(name, False),
                }
                for name, m in mules_r.items()
            ]
        )

    status_msg = {
        "type": "fleet_status",
        "fleet": fleet,
        "entity_type": entity_type,
        "status": statuses,
        "fleet_status": fleet_status,
    }
    send_msg_to_frontend(status_msg, fleet)


def handle_mule_recovery(mule_r, curr_pose, redis: FleetRedis):
    next_pose = mule_r["next_pose"]
    next_dest = mule_r["next_dest"]
    mule_name = mule_r["name"]
    last_totes_moved = mule_r.get("last_totes_moved")
    num_totes = mule_r["num_totes"]
    next_msg = None
    conveyor_r = None
    fleet_name = redis.fleet_name

    fleet_r = Fleet.from_json(redis.get("fleet"))
    if mule_name in fleet_r.mules_init_sent:
        # this is for handling init initiated by the fleet manager.
        init_sent = True
        fleet_r.mules_init_sent.remove(mule_name)
        redis.set("fleet", fleet_r.to_json())
    else:
        init_sent = False

    if next_pose and not are_poses_close(curr_pose, next_pose, mule_name):
        # mule did not reach where we sent it. Send another move command.
        send_move_to_msg(mule_r, next_pose, redis)
        get_logger(mule_name).info(
            f"[update] telling mule {mule_name} at {curr_pose} to move to {next_pose}"
        )
        if mule_r["action"] == MuleActions.PICKUP:
            update_mule_next_dest(mule_r, redis, init_sent)
        return None

    last_msg_recv = mule_r["last_msg_recv"]
    last_msg_type = FleetMessages.get_msg_type(last_msg_recv)
    last_cmd_sent = mule_r["last_cmd_sent"]
    last_msg_recv = json.loads(last_msg_recv) if last_msg_recv else None
    mule_r["is_disabled"] = True if (last_msg_type == FleetMessages.CONV_ERROR and last_cmd_sent != FleetCommands.RESET_TOTES) else False

    if not next_dest or (
        mule_r["action"] == MuleActions.PARK and not mule_r["is_disabled"]
    ):
        mule_r, station = send_mule_to_park_from_pose(mule_r, redis)
        get_logger(mule_name).info(
            f"[update] sent mule {mule_name} at {curr_pose} to park at {station}"
        )
        return None

    get_logger(mule_name).info(
        f"recovery[{mule_name}]:last_cmd:{last_cmd_sent},last_msg:{last_msg_type}"
    )
    invalid_state = False
    update_tote_status = False

    reached_dest_msg = add_extra_fields_to_mule_msg(
        {
            "type": "reached",
            "destination": next_pose,
            "fleet": fleet_name,
        },
        mule_name,
    )

    conv_completed_msg = add_extra_fields_to_mule_msg(
        {
            "type": "conveyor",
            "completed": True,
            "started": False,
            "totes_moved": last_totes_moved,
            "tote_stuck": False,
            "tote_overload": False,
            "tote_count_mismatch": False,
            "error_flag": False,
            "fleet": fleet_name,
        },
        mule_name,
    )

    if last_msg_type == FleetMessages.REACHED:
        if last_cmd_sent in {
            FleetCommands.MOVE_TO_CONV,
            FleetCommands.START_CONV_RECV,
        }:
            mule_r["action"] = MuleActions.PICKUP
            update_tote_status = True
            next_msg = last_msg_recv
        elif last_cmd_sent in {
            FleetCommands.MOVE_TO_CHUTE,
            FleetCommands.START_CONV_SEND,
        }:
            mule_r["action"] = MuleActions.DROP
            next_msg = last_msg_recv
        elif last_cmd_sent == FleetCommands.MOVE_TO_PARK:
            pass
            # send_init_recd_msg()
        elif last_cmd_sent == FleetCommands.MOVE_TO_CHARGE:
            pass
        else:
            invalid_state = True

    elif last_msg_type == FleetMessages.CONV_STARTED:
        if last_cmd_sent in {
            FleetCommands.START_CONV_RECV,
            FleetCommands.TRANSFER_TOTES,
        }:
            update_tote_status = True
            # if num_totes > 0 we assume the tote transfer is complete.
            next_msg = conv_completed_msg if num_totes > 0 else reached_dest_msg
        elif last_cmd_sent == FleetCommands.START_CONV_SEND:
            # if num_totes == 0 we assume the tote transfer is complete.
            next_msg = conv_completed_msg if num_totes == 0 else reached_dest_msg
        else:
            invalid_state = True

    elif last_msg_type == FleetMessages.CONV_COMPLETED:
        if last_cmd_sent in {
            FleetCommands.START_CONV_RECV,
            FleetCommands.TRANSFER_TOTES,
        }:
            update_tote_status = True
            next_msg = last_msg_recv
        elif last_cmd_sent == FleetCommands.START_CONV_SEND:
            next_msg = last_msg_recv
        elif last_cmd_sent in {
            FleetCommands.MOVE_TO_CHUTE,
            FleetCommands.MOVE_TO_PARK,
        }:
            next_msg = reached_dest_msg
        elif last_cmd_sent == FleetCommands.MOVE_TO_CONV:
            # mule reached conveyor for next pickup.
            update_tote_status = True
            next_msg = reached_dest_msg
        else:
            invalid_state = True

    elif last_msg_type == FleetMessages.CONV_ERROR:
        if last_cmd_sent != FleetCommands.RESET_TOTES:
            action = mule_r["action"]
            if action == MuleActions.PICKUP or action == MuleActions.DROP:
                next_msg = last_msg_recv
                get_logger(mule_name).info(
                    f"trying to recover mule {mule_name} after error in {MuleActions.to_str(action)}"
                )
                update_tote_status = True

    elif last_msg_type == FleetMessages.NONE:
        if last_cmd_sent in {
            FleetCommands.MOVE_TO_CONV,
        }:
            update_tote_status = True
            next_msg = reached_dest_msg
        elif last_cmd_sent in {
            FleetCommands.MOVE_TO_CHUTE,
            FleetCommands.MOVE_TO_PARK,
        }:
            next_msg = reached_dest_msg
        elif last_cmd_sent == FleetCommands.START_CONV_RECV:
            update_tote_status = True
            # if num_totes > 0 we assume the tote transfer is complete.
            if num_totes > 0:
                next_msg = conv_completed_msg
            else:
                next_msg = reached_dest_msg
                mule_r["action"] = MuleActions.PICKUP
        elif last_cmd_sent == FleetCommands.START_CONV_SEND:
            # if num_totes == 0 we assume the tote transfer is complete.
            if num_totes == 0:
                next_msg = conv_completed_msg
            else:
                next_msg = reached_dest_msg
                mule_r["action"] = MuleActions.DROP

    # update status of mule's next dest -- could be conveyor, chute, parking, charging
    update_mule_next_dest(mule_r, redis, update_tote_status and init_sent)

    if invalid_state:
        raise Exception(
            f"recovery[{mule_r['name']}]:last_cmd:{last_cmd_sent},last_msg:{last_msg_type} invalid pair"
        )
    elif next_msg:
        # remove seq_num from next_msg if it exists, otherwise it may interfere with
        # sequence number tracking if this message comes from the previous run (prior to a
        # new init resetting the sequence number to 1).
        next_msg.pop("seq_num", None)
        add_to_dispatcher_queue(next_msg)

    return conveyor_r


def should_handle_msg(msg, redis):
    seq_num = msg.get("seq_num")
    name = msg.get("name")
    fleet = msg.get("fleet")
    msg_type = FleetMessages.get_msg_type(msg)

    fleet_r = Fleet.from_json(redis.get("fleet"))
    if not fleet_r.initialized and msg_type != FleetMessages.FLEET_START:
        start_msg = {"type": "control", "fleet": fleet, "command": "start"}
        add_to_dispatcher_queue(start_msg)
        reason = f"fleet {fleet} not started"
        return False, reason

    all_mules_r = redis.get_redis_mules()
    mule_r = all_mules_r.get(name)

    if not mule_r:
        return True, None

    if not mule_r["initialized"] and msg_type == FleetMessages.VERIFY_MULE_MAP:
        return True, None

    if not mule_r["initialized"] and msg_type != FleetMessages.INIT:
        return False, f"mule {name} not initialized"

    if not seq_num:
        return True, None

    if seq_num > mule_r["last_seq_num"] or msg_type == FleetMessages.INIT:
        mule_r["last_seq_num"] = seq_num
        redis.update_redis([], [mule_r], None, all_mules_r)
        return True, None
    else:
        reason = f"seq_num {seq_num} is old"
        return False, reason


def handle_fleet_start(msg, redis: FleetRedis):
    mules_init_sent = []
    fleet = Fleet.from_json(redis.get("fleet"))
    redis.update_entity("start", "fleet_status")
    redis.update_entity(False, "fleet_stop")

    if fleet.initialized:
        get_logger(fleet.name).info(f"fleet {fleet.name} already started")
        return
    all_mules_r: dict = redis.get_redis_mules()

    for mule_r in all_mules_r.values():
        send_fleet_init_msg(mule_r)
        mules_init_sent.append(mule_r["name"])
    fleet.mules_init_sent = mules_init_sent
    fleet.initialized = True
    get_logger(fleet.name).info(f"fleet {fleet.name} started")
    redis.set("fleet", fleet.to_json())


def handle_fleet_stop(msg, redis: FleetRedis):
    redis.update_entity("stop", "fleet_status")
    redis.update_entity(True, "fleet_stop")


def handle_fleet_resume_pause(msg, redis: FleetRedis):
    all_mules_r = redis.get_any_entity("mules")
    command = msg["action"]

    # send ack to toggle UI button status
    send_ack_to_frontend(msg)
    redis.update_entity(command, "fleet_status")

    fleet_stop = True if command == "pause" else False
    redis.update_entity(fleet_stop, "fleet_stop")

    for mule_name, mule_r in all_mules_r.items():
        resume_pause_msg = {
            "mule": mule_name,
            "action": "startstop",
            "command": command,
            "fleet": redis.fleet_name,
        }
        handle_resume_pause_mule(resume_pause_msg, redis)


def handle_fleet_emergency_stop(msg, redis: FleetRedis):
    all_mules_r = redis.get_any_entity("mules")
    redis.update_entity("emergency_stop", "fleet_status")
    redis.update_entity(True, "fleet_stop")
    if msg["kill"]:
        for mule_name, mule_r in all_mules_r.items():
            emergency_stop_msg = {
                "mule": mule_name,
                "type": "mode_switch",
                "mode": "stop",
                "fleet": redis.fleet_name,
            }
            enqueue(to_mule_queue, send_to_mule, emergency_stop_msg)
    else:
        msg["action"] = "pause"
        handle_fleet_resume_pause(msg, redis)


def handle_update_all_mule_map(msg, redis):
    all_mules_r = redis.get_any_entity("mules")
    for mule_name, mule_r in all_mules_r.items():
        msg["mule_name"] = mule_name
        handle_update_mule_map(msg, redis)


def handle_update_mule_map(msg, redis):
    mule_name = msg["mule_name"]
    update_map_msg = {"mule": mule_name, "action": "update_map"}
    enqueue(to_mule_queue, send_to_mule, update_map_msg)
    get_logger(mule_name).info(f"sending a update map request to {mule_name}")
    get_logger(redis.fleet_name).info(f"sending a update map request to {mule_name}")


def handle_verify_mule_map(msg, redis):
    mule_name = msg["name"]
    map_files_to_check = json.loads(msg["map_info"])

    db = get_db_session()
    # obtain fleet_id using mule_name
    db_mule = get_values_from_db(db, "mules", "name", mule_name)[0]
    fleet_id = db_mule.fleet_id
    # obtain map id using fleet_id
    _, fleet_name_db, _, _, _, map_id, _, _ = get_values_from_db(
        db, "fleets", "id", fleet_id
    )[0]

    invalid_map_files, map_files_checked = check_mule_map_files(
        map_files_to_check, map_id, redis.fleet_name
    )

    if invalid_map_files:
        get_logger(mule_name).info(f"{mule_name} has invalid map files")
        get_logger(redis.fleet_name).info(f"{mule_name} has invalid map files ")

    verify_map_msg = {
        "mule": mule_name,
        "action": "verify_map",
        "map_info": map_files_checked,
        "fleet": redis.fleet_name,
    }
    enqueue(to_mule_queue, send_to_mule, verify_map_msg)


def handle_resume_pause_mule(msg, redis: FleetRedis):

    try:
        mule_name = msg["mule_name"]
    except:
        mule_name = msg["mule"]

    command = msg["command"]

    resume_pause_msg = {
        "mule": mule_name,
        "action": "startstop",
        "command": command,
        "fleet": redis.fleet_name,
    }
    enqueue(to_mule_queue, send_to_mule, resume_pause_msg)

    mule_emergency_stop_dict = redis.get_any_entity("mule_emergency_stop_dict")
    mule_emergency_stop_dict[mule_name] = True if command == "pause" else False
    redis.update_entity(mule_emergency_stop_dict, "mule_emergency_stop_dict")
    get_logger(mule_name).info(f"{mule_name} recieved a command to {command}")
    get_logger(redis.fleet_name).info(f"{mule_name} recieved a command to {command}")

    if msg.get("shutdown", False):
        get_logger(mule_name).info(f"Got shutdown request for {mule_name} from UI")
        all_mules_r = redis.get_any_entity("mules")
        mule_r = all_mules_r[mule_name]
        mule_r, _ = handle_mule_shutdown(mule_r, redis)
        mule_r["next_dest"] = None
        mule_r["next_pose"] = None
        all_mules_r[mule_name] = mule_r
        redis.update_entity(all_mules_r, "mules")

    msg["type"] = "mule_control"
    send_ack_to_frontend(msg)


def handle_dispatcher_msgs(msg, internal=False):
    name = msg.get("name")
    fleet = msg.get("fleet")
    if not fleet:
        _redis = get_redis()
        station_fleet_mapping = json.loads(_redis.get("station_fleet_mapping"))
        fleet = station_fleet_mapping.get(name, None)
        if not fleet:
            raise ValueError("Fleet name missing in dispatcher message")
        else:
            msg["fleet"] = fleet

    redis: FleetRedis = get_redis(fleet)
    update_msg = True

    # don't log status messages to disaggregated logs
    logger = (
        get_logger(fleet)
        if FleetMessages.is_frequent_msg(msg) or not name
        else get_logger(name)
    )
    logger.info(f"processing message: {msg}")

    handle_ok, reason = should_handle_msg(msg, redis)
    if not handle_ok:
        get_logger(name).info(f"ignoring message {msg}: {reason}")
        return

    mule_r = redis.get_redis_mules().get(name)

    if not internal and mule_r:
        send_ack_msg(msg)

    msg_type = FleetMessages.get_msg_type(msg)
    if msg_type == FleetMessages.TOTE_STATUS:
        handle_tote_status(msg, redis)
    elif msg_type == FleetMessages.REACHED:
        if not handle_reached_destination(msg, redis, internal):
            update_msg = False
    elif msg_type == FleetMessages.CONV_STARTED:
        handle_conveyor_started(msg, redis)
    elif msg_type == FleetMessages.CONV_COMPLETED:
        handle_conveyor_completed(msg, redis)
    elif msg_type == FleetMessages.CONV_ERROR:
        handle_conveyor_error(msg, redis)
    elif msg_type == FleetMessages.VISA_REQUEST:
        handle_visa_request(msg, redis)
    elif msg_type == FleetMessages.VISA_RELEASE:
        handle_visa_release(msg, redis)
    elif msg_type == FleetMessages.TRIP_STATUS:
        handle_trip_status(msg, redis)
    elif msg_type == FleetMessages.BATTERY_STATUS:
        handle_battery_status(msg, redis)
    elif msg_type == FleetMessages.RECHARGE:
        pass
        # handle_mule_recharge(msg, redis)
    elif msg_type == FleetMessages.INIT:
        handle_mule_init(msg, redis)
        update_msg = False
    elif msg_type == FleetMessages.FLEET_START:
        handle_fleet_start(msg, redis)
    elif msg_type == FleetMessages.FLEET_STOP:
        handle_fleet_stop(msg, redis)
    elif msg_type == FleetMessages.FLEET_EMERGENCY_STOP:
        handle_fleet_emergency_stop(msg, redis)
    elif msg_type == FleetMessages.FLEET_RESUME_PAUSE:
        handle_fleet_resume_pause(msg, redis)
    elif msg_type == FleetMessages.FLEET_BATTERY_SWAP:
        handle_battery_swap(msg, redis)
    elif msg_type == FleetMessages.FLEET_STATUS_REQUEST:
        handle_fleet_status_request(msg, redis)
    elif msg_type == FleetMessages.CHANGE_STATION_STATUS:
        handle_change_station_status(msg, redis)
    elif msg_type == FleetMessages.CHANGE_MULE_STATUS:
        handle_change_mule_status(msg, redis)
    elif msg_type == FleetMessages.ISSUE_STATUS:
        handle_issue_status(msg, redis)
    elif msg_type == FleetMessages.TOTE_RESET_ACK:
        handle_tote_reset_ack(msg, redis)
    elif msg_type == FleetMessages.RESUME_PAUSE_MULE:
        handle_resume_pause_mule(msg, redis)
    elif msg_type == FleetMessages.UPDATE_MULE_MAP:
        handle_update_mule_map(msg, redis)
    elif msg_type == FleetMessages.UPDATE_ALL_MULE_MAP:
        handle_update_all_mule_map(msg, redis)
    elif msg_type == FleetMessages.VERIFY_MULE_MAP:
        handle_verify_mule_map(msg, redis)
    elif msg_type == FleetMessages.MULE_BATTERY_SWAP:
        handle_mule_battery_swap(msg, redis)
    elif msg_type:
        get_logger(name).error(f"unsupported message of type {msg_type} from {name}")
        update_msg = False

    all_mules_r = redis.get_redis_mules()
    mule_r = all_mules_r.get(name)
    if update_msg and mule_r and not should_forget_msg(msg):
        mule_r["last_msg_recv"] = json.dumps(msg)
        redis.update_redis([], [mule_r], None, all_mules_r)


fleet_handlers = {
    FleetMessages.CONV_STARTED: handle_conveyor_started,
    FleetMessages.CONV_COMPLETED: handle_conveyor_completed,
    FleetMessages.VISA_REQUEST: handle_visa_request,
    FleetMessages.VISA_RELEASE: handle_visa_release,
    FleetMessages.TRIP_STATUS: handle_trip_status,
    FleetMessages.CHANGE_STATION_STATUS: handle_change_station_status,
    FleetMessages.BATTERY_STATUS: handle_battery_status,
    FleetMessages.TOTE_STATUS: handle_tote_status,
    # FleetMessages.NONE: handle_unsupported_msg,
}
