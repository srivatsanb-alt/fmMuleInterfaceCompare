import datetime
import inspect
import numpy as np
import secrets
import string


TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def check_if_timestamp_has_passed(dt):
    return dt < datetime.datetime.now()


def dt_to_str(dt):
    return datetime.datetime.strftime(dt, TIME_FORMAT)


def str_to_dt(dt_str):
    return datetime.datetime.strptime(dt_str, TIME_FORMAT)


def str_to_ts(dt_str):
    return datetime.datetime.strptime(dt_str, TIME_FORMAT).timestamp()


def are_poses_close(pose1, pose2, threshold=0.8):
    pose1 = np.array(pose1)
    pose2 = np.array(pose2)
    xy_close = np.linalg.norm(pose1[:2] - pose2[:2]) <= threshold
    # theta_close = np.abs(normalize(pose1[2] - pose2[2])) <= 0.1
    # return xy_close and theta_close
    return xy_close


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


def generate_random_job_id():
    N = 10
    return "".join(secrets.choice(string.ascii_uppercase + string.digits) for i in range(N))
