import redis
import json
import time
import os
import sys
import numpy as np
import logging
import logging.config
from utils.router_utils import get_dense_path


# ati code imports
import utils.log_utils as lu
from models.db_session import DBSession

# to avoid mule router module logs
logging.getLogger().level == logging.ERROR

# get log config
logging.config.dictConfig(lu.get_log_config_dict())


sys.path.append("/app")
from utils.util import are_poses_close
from utils.router_utils import AllRouterModules


def init_routers():
    with DBSession() as dbsession:
        fleet_names = dbsession.get_all_fleet_names()
    all_router_modules = AllRouterModules(fleet_names)
    return all_router_modules


def start_router_module():
    redis_conn = redis.from_url(os.getenv("FM_REDIS_URI"))
    logger = logging.getLogger("control_module_router")
    all_router_modules = init_routers()
    logger.info(f"Intialized the router modules")

    while True:
        add_router_for = redis_conn.get("add_router_for")
        update_router_for = redis_conn.get("update_router_for")

        if add_router_for is not None:
            fleet_name = add_router_for.decode()
            all_router_modules.add_router_module(fleet_name)
            redis_conn.delete("add_router_for")
            logger.info(f"Added router module for {fleet_name}")

        if update_router_for is not None:
            fleet_name = update_router_for.decode()
            all_router_modules.add_router_module(fleet_name)
            redis_conn.delete("update_router_for")
            logger.info(f"Updated router module for {fleet_name}")

        for key in redis_conn.keys("control_router_rl_job_*"):
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
                    route_length = redis_conn.get(f"rl_{str(pose_1)}_{str(pose_2)}")
                    if route_length is None:
                        route_length = rm.get_route_length(pose_1, pose_2)
                        redis_conn.set(f"rl_{str(pose_1)}_{str(pose_2)}", route_length)
                    else:
                        route_length = float(route_length)
                except Exception as e:
                    logger.info(
                        f"unable to find route length between {pose_1} and {pose_2} of {fleet_name} \n Exception {e}"
                    )
                    route_length = json.dumps(np.inf)

            redis_conn.setex(
                f"result_{job_id}",
                int(redis_conn.get("default_job_timeout_ms").decode()),
                route_length,
            )

            logger.info(f"Result : {control_router_rl_job} - {route_length}")
            redis_conn.delete(key)

        for key in redis_conn.keys("control_router_wps_job_*"):
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

            redis_conn.setex(
                f"result_wps_job_{job_id}",
                int(redis_conn.get("default_job_timeout_ms").decode()),
                json.dumps(wps_list),
            )

        for key in redis_conn.keys("control_router_dp_rl_job_*"):
            str_job = redis_conn.get(key)
            logger.info(f"Got a dp_rl job {str_job}")
            control_router_get_route_job = json.loads(str_job)
            pose_1 = control_router_get_route_job[0]
            pose_2 = control_router_get_route_job[1]
            fleet_name = control_router_get_route_job[2]
            job_id = control_router_get_route_job[3]
            rm = all_router_modules.get_router_module(fleet_name)

            route_length = 0
            dp_rl_result = [[], [], [], 0]
            if not are_poses_close(pose_1, pose_2):
                try:
                    final_route, visa_obj, rl = rm.get_route(pose_1, pose_2)
                    x_vals, y_vals, t_vals, _ = get_dense_path(final_route)
                    dp_rl_result = [x_vals.tolist(), y_vals.tolist(), t_vals.tolist(), rl]
                except Exception as e:
                    logger.info(
                        f"unable to find route between {pose_1} and {pose_2} of {fleet_name} \n Exception {e}"
                    )

            redis_conn.setex(
                f"result_dp_rl_job_{job_id}",
                int(redis_conn.get("default_job_timeout_ms").decode()),
                json.dumps(dp_rl_result),
            )
            redis_conn.delete(key)

        time.sleep(0.2)


if __name__ == "__main__":
    while True:
        try:
            start_router_module()
        except Exception as e:
            logging.getLogger().error(f"Exception in router, exception: {e}")
            time.sleep(10)
