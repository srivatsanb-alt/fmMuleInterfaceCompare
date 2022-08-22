from datetime import datetime

import numpy as np


TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def ts_to_str(ts):
    return (datetime.strftime(datetime.fromtimestamp(ts), TIME_FORMAT),)


def are_poses_close(pose1, pose2, threshold=0.8):
    pose1 = np.array(pose1)
    pose2 = np.array(pose2)
    xy_close = np.linalg.norm(pose1[:2] - pose2[:2]) <= threshold
    # theta_close = np.abs(normalize(pose1[2] - pose2[2])) <= 0.1
    # return xy_close and theta_close
    return xy_close
