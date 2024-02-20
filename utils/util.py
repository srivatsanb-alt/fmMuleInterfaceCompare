import datetime
import inspect
import numpy as np
import secrets
import string
import toml
import os
import psutil
import redis
import json
import yaml
import time
import logging
from rq import Worker
import sys
import functools

TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
IES_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"


def get_mule_config():
    return toml.load(os.getenv("ATI_CONSOLIDATED_CONFIG"))


def check_if_timestamp_has_passed(dt):
    return dt < datetime.datetime.now()


def dt_to_str(dt):
    return datetime.datetime.strftime(dt, TIME_FORMAT)


def str_to_dt(dt_str):
    return datetime.datetime.strptime(dt_str, TIME_FORMAT)


def str_to_ts(dt_str):
    return datetime.datetime.strptime(dt_str, TIME_FORMAT).timestamp()


def str_to_dt_UTC(dt_str):
    return datetime.datetime.strptime(dt_str, IES_TIME_FORMAT + " %z")


def are_poses_close(pose1, pose2):
    mule_config = get_mule_config()
    threshold = mule_config.get("control").get("common").get("station_dist_thresh", 0.8)
    pose1 = np.array(pose1)
    pose2 = np.array(pose2)
    xy_close = np.linalg.norm(pose1[:2] - pose2[:2]) <= threshold
    return xy_close


def get_table_as_dict(model, model_obj):
    all_valid_types = ["str", "dict", "list", "int", "float", "bool"]
    cols = [(c.name, c.type.python_type.__name__) for c in model.__table__.columns]
    result = {}
    model_dict = model_obj.__dict__
    for col, col_type in cols:
        value = model_dict.get(col, None)
        if isinstance(value, datetime.datetime):
            result.update({col: dt_to_str(value)})
        elif inspect.isclass(value):
            pass
        elif col_type not in all_valid_types:
            pass
        else:
            if isinstance(value, list):
                skip = False
                for item in value:
                    if type(item).__name__ not in all_valid_types:
                        skip = True
                        break
                if skip:
                    continue
            result.update({col: value})
    return result


def generate_random_job_id():
    N = 10
    return "".join(secrets.choice(string.ascii_uppercase + string.digits) for i in range(N))


def get_all_map_names():
    map_names = []
    _ = os.system(
        "find $FM_STATIC_DIR -name 'map' -printf '%h\n' | awk -'F/' '{ print $NF }' > /app/static/map_names.txt"
    )
    map_names_file = open(os.path.join(os.getenv("FM_STATIC_DIR"), "map_names.txt"), "r")
    for line in map_names_file.readlines():
        map_names.append(line[:-1])

    return map_names


def sys_perf():
    ONE_GB = 1024**3

    cpu = psutil.cpu_times_percent()
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    net = psutil.net_io_counters()
    cpu_count = psutil.cpu_count()
    load_avg = psutil.getloadavg()
    cpu_freq = psutil.cpu_freq()

    column_names = [
        "datetime",
        "cpu_user",
        "cpu_system",
        "cpu_idle",
        "cpu_count",
        "cpu_freq",
        "mem_available_gb",
        "mem_used_gb",
        "swap_used_gb",
        "load_avg_1",
        "load_avg_5",
        "load_avg_15",
        "net_packets_sent",
        "net_packets_recv",
        "net_errin",
        "net_errout",
    ]

    data = [
        dt_to_str(datetime.datetime.now()),
        cpu.user,
        cpu.system,
        cpu.idle,
        cpu_count,
        cpu_freq.current if cpu_freq else None,
        np.round(mem.available / ONE_GB, 3),
        np.round(mem.used / ONE_GB, 3),
        np.round(swap.used / ONE_GB, 3),
        load_avg[0],
        load_avg[1],
        load_avg[2],
        net.packets_sent,
        net.packets_recv,
        net.errin,
        net.errout,
    ]

    return column_names, data


def rq_perf():
    redis_conn = redis.from_url(os.getenv("FM_REDIS_URI"))
    data = []
    workers = Worker.all(connection=redis_conn)

    column_names = [
        "datetime",
        "worker_name",
        "worker_pid",
        "worker_state",
        "worker_queues",
        "num_jobs",
        "successful_job_count",
        "failed_job_count",
        "total_working_time",
    ]

    for worker in workers:
        wqs = worker.queues
        worker_data = [
            dt_to_str(datetime.datetime.now()),
            worker.name,
            worker.pid,
            worker.state,
            [wq.name for wq in wqs],
            [len(wq) for wq in wqs],
            worker.successful_job_count,
            worker.failed_job_count,
            worker.total_working_time,
        ]
        data.append(worker_data)

    return column_names, data


def get_route_length(pose_1, pose_2, fleet_name, redis_conn=None):
    job_id = generate_random_job_id()

    if redis_conn is None:
        redis_conn = redis.from_url(os.getenv("FM_REDIS_URI"))

    route_length = redis_conn.get(f"rl_{str(pose_1)}_{str(pose_2)}")
    if route_length is None:
        control_router_rl_job = [pose_1, pose_2, fleet_name, job_id]
        redis_conn.setex(
            f"control_router_rl_job_{job_id}",
            int(redis_conn.get("default_job_timeout_ms").decode()),
            json.dumps(control_router_rl_job),
        )
        while not redis_conn.get(f"result_{job_id}"):
            time.sleep(0.005)

        route_length = json.loads(redis_conn.get(f"result_{job_id}"))
        redis_conn.delete(f"result_{job_id}")
    else:
        route_length = float(route_length)

    return route_length


def check_if_notification_alert_present(dbsession, log: str, enitity_names: list):
    import models.misc_models as mm

    notification = (
        dbsession.session.query(mm.Notifications)
        .filter(mm.Notifications.entity_names == enitity_names)
        .filter(mm.Notifications.log == log)
        .all()
    )
    if len(notification):
        return True
    return False


def maybe_add_notification(
    dbsession, enitity_names: list, log: str, log_level=None, module=None
):
    import models.misc_models as mm

    if log_level is None:
        log_level = mm.NotificationLevels.info
    if module is None:
        module = mm.NotificationModules.generic

    if not check_if_notification_alert_present(dbsession, log, enitity_names):
        dbsession.add_notification(enitity_names, log, log_level, module)


def get_closest_station(dbsession, pose, fleet_name):
    temp = None
    all_stations = dbsession.get_all_stations_in_fleet(fleet_name)
    for station in all_stations:
        if are_poses_close(pose, station.pose):
            temp = station
            break

    return temp


def read_docker_compose_yml():
    fm_version = os.getenv("FM_TAG")
    with open(f"/app/static/docker_compose_v{fm_version}.yml") as f:
        data = yaml.safe_load(f)

    return data


def good_password_check(password):
    upper_case = False
    special_char = False

    if len(password) < 8:
        return False

    for c in password:
        if not (c.isalpha() or c.isdigit() or c == " "):
            special_char = True
        if c.isupper():
            upper_case = True
        if special_char and upper_case:
            return True

    return False


def write_fm_error_to_json_file(module: str, error_detail: dict):
    random_id = generate_random_job_id()
    dir_to_save = os.path.join(os.getenv("FM_STATIC_DIR"), "fm_errors")
    fm_errors_path = os.path.join(
        os.getenv("FM_STATIC_DIR"), "fm_errors", f"{module}_{random_id}.log"
    )
    if not os.path.exists(dir_to_save):
        os.makedirs(dir_to_save)
    error_detail["random_id"] = random_id
    try:
        with open(fm_errors_path, "w") as f:
            json.dump(error_detail, f, default=str)
    except Exception as e:
        logging.getLogger().info(f"Error occurred when trying to write to file: {e}")


def proc_exception(func, e):
    error_dict = {
        "module": func.__name__,
        "error_type": type(e).__name__,
        "error_msg": str(e),
        "code": "generic",
    }

    db_strs = ["psycop", "sqlalchemy"]

    if any([db_str in error_dict["error_msg"] for db_str in db_strs]):
        error_dict["code"] = "db"

    write_fm_error_to_json_file(error_dict["module"], error_dict)
    logging.info(
        f"Error occurred when trying to Monitor the Process {error_dict['module']}: {e}"
    )
    sys.exit(1)


def report_error(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            proc_exception(func, e)

    return wrapper


def proc_retry(times=np.inf, sleep_time=5):
    def decorator(func):
        def wrapper(*args, **kwargs):
            attempt = 0
            while attempt < times:
                try:
                    return func(*args, **kwargs)
                except:
                    attempt += 1
                    time.sleep(sleep_time)
            return func(*args, **kwargs)

        return wrapper

    return decorator


def async_report_error(func):
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        try:
            result = await func(*args, **kwargs)
            return result
        except Exception as e:
            logging.exception(f"Exception occurred in {func.__name__}: {e}")
            proc_exception(func, e)
            raise e

    return async_wrapper


def format_fm_incident(fm_incident):
    temp = {}
    temp.update({"code": fm_incident.code})
    temp.update({"message": fm_incident.message})
    temp.update({"description": fm_incident.display_message})
    temp.update({"how_to_recover": fm_incident.recovery_message})
    temp.update({"reported_at": dt_to_str(fm_incident.created_at)})
    temp.update({"module": fm_incident.module})
    temp.update({"other_info": fm_incident.other_info})
    return temp
