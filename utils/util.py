import datetime
import inspect
import numpy as np
import secrets
import string
import toml
import os


TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
IES_TIME_FORMAT = "%Y-%m-%dT%H:%M:%S"


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
        "find $FM_MAP_DIR -name 'map' -printf '%h\n' | awk -'F/' '{ print $NF }' > /app/static/map_names.txt"
    )
    map_names_file = open(os.path.join(os.getenv("FM_MAP_DIR"), "map_names.txt"), "r")
    for line in map_names_file.readlines():
        map_names.append(line[:-1])

    return map_names
