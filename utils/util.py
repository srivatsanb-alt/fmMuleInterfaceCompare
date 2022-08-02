from datetime import datetime

import numpy as np

from core.logs import get_logger


TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def ts_to_str(ts):
    return (datetime.strftime(datetime.fromtimestamp(ts), TIME_FORMAT),)


def are_poses_close(pose1, pose2, mule_name, threshold=0.8):
    pose1 = np.array(pose1)
    pose2 = np.array(pose2)
    get_logger(mule_name).debug(f"Comparing poses {pose1},{pose2}")
    xy_close = np.linalg.norm(pose1[:2] - pose2[:2]) <= threshold
    # theta_close = np.abs(normalize(pose1[2] - pose2[2])) <= 0.1
    get_logger(mule_name).debug(f"xy close? {xy_close}")
    # pylogging.info(f"theta close? {theta_close}")
    # return xy_close and theta_close
    return xy_close
