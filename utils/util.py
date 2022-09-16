from datetime import datetime
import time
import numpy as np


TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def check_if_timestamp_has_passed(dt_str):
    return dt_str < datetime.now()


def ts_to_str(ts):
    return datetime.strftime(datetime.fromtimestamp(ts), TIME_FORMAT)


def str_to_ts(dt_str):
    return datetime.strftime(dt_str, TIME_FORMAT).timestamp()


def are_poses_close(pose1, pose2, threshold=0.8):
    pose1 = np.array(pose1)
    pose2 = np.array(pose2)
    xy_close = np.linalg.norm(pose1[:2] - pose2[:2]) <= threshold
    # theta_close = np.abs(normalize(pose1[2] - pose2[2])) <= 0.1
    # return xy_close and theta_close
    return xy_close


def get_epoch_time(hh: int, mm: int) -> float:
    """Will convert time from hh:mm format to epoch time"""
    tn = time.localtime()
    new_time = time.struct_time(
        (tn.tm_year, tn.tm_mon, tn.tm_mday, hh, mm, 0, tn.tm_wday, tn.tm_yday, tn.tm_isdst)
    )
    return time.mktime(new_time)
