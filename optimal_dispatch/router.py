import redis
import json
import time
import numpy as np
import sys

sys.path.append("/app")
from utils.util import are_poses_close
from utils.router_utils import AllRouterModules
import os
from core.logs import get_logger


def start_router_module():
    all_router_modules = AllRouterModules()
    redis_conn = redis.from_url(os.getenv("FM_REDIS_URI"))
    logger = get_logger("control_router_module")

    logger.info("starting control router module")

    while True:
        for key in redis_conn.scan_iter("control_router_job_*"):
            str_job = redis_conn.get(key)
            logger.info(f"Got a route length estimation job {str_job}")
            control_router_job = json.loads(str_job)
            pose_1 = control_router_job[0]
            pose_2 = control_router_job[1]
            fleet_name = control_router_job[2]
            job_id = control_router_job[3]
            rm = all_router_modules.get_router_module(fleet_name)

            route_length = 0
            if not are_poses_close(pose_1, pose_2):
                try:
                    route_length = rm.get_route_length(pose_1, pose_2)
                except Exception as e:
                    logger.info(
                        f"unable to find route length between {pose_1} and {pose_2} of {fleet_name} \n Exception {e}"
                    )
                    route_length = json.dumps(np.inf)

            redis_conn.set(f"result_{job_id}", route_length)
            logger.info(f"Result : {control_router_job} - {route_length}")
            redis_conn.delete(key)

        time.sleep(1e-2)


if __name__ == "__main__":
    start_router_module()
