import redis
import json
import time
import os
import logging
import sys
import numpy as np

from models.db_session import DBSession


# to avoid mule router module logs
logging.getLogger().level == logging.ERROR

sys.path.append("/app")
from core.logs import get_seperate_logger
from utils.util import are_poses_close
from utils.router_utils import AllRouterModules


def start_router_module():

    with DBSession() as dbsession:
        fleet_names = dbsession.get_all_fleet_names()

    all_router_modules = AllRouterModules(fleet_names)
    redis_conn = redis.from_url(os.getenv("FM_REDIS_URI"))

    logger = get_seperate_logger("control_module_router")

    while True:
        for key in redis_conn.scan_iter("control_router_rl_job_*"):
            str_job = redis_conn.get(key)
            logger.info(f"Got a route length estimation job {str_job}")
            control_router_rl_job = json.loads(str_job)
            pose_1 = control_router_rl_job[0]
            pose_2 = control_router_rl_job[1]
            fleet_name = control_router_rl_job[2]
            job_id = control_router_rl_job[3]
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
            logger.info(f"Result : {control_router_rl_job} - {route_length}")
            redis_conn.delete(key)

        for key in redis_conn.scan_iter("control_router_wps_job_*"):
            try:
                str_job = redis_conn.get(key)
                logger.info(f"got a route preview estimation job {str_job}")
                control_router_wps_job = json.loads(str_job)
                station_poses = control_router_wps_job[0]
                fleet_name = control_router_wps_job[1]
                job_id = control_router_wps_job[2]
                rm = all_router_modules.get_router_module(fleet_name)

                start_pose = station_poses[0]
                dest_poses = station_poses[1:]
                wps_list = rm.get_path_wps(start_pose, dest_poses)
                logger.info(f"result of wps req: {wps_list}")
                redis_conn.delete(key)

            except Exception as e:
                logger.info(
                    f"unable to get route for poses {station_poses} \n Exception {e}"
                )
                wps_list = []

            redis_conn.set(f"result_wps_job_{job_id}", json.dumps(wps_list))

        time.sleep(0.3)


if __name__ == "__main__":
    start_router_module()
