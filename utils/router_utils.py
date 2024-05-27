import sys
import os
import logging

# ati code imports
import utils.util as utils_util

sys.path.append(os.environ["MULE_ROOT"])
from mule.ati.control.bridge.router_planner_interface import RoutePlannerInterface
import mule.ati.control.dynamic_router.grid_route_library as grl


def get_dense_path(final_route):
    return grl.get_dense_path(final_route)


class RouterModule:
    def __init__(self, map_path):
        self.gmaj_path = os.path.join(map_path, "grid_map_attributes.json")
        os.environ["ATI_MAP"] = map_path
        self.router = RoutePlannerInterface(self.gmaj_path).router

    def get_path_wps(self, start_pose, dest_poses):
        return self.router.generate_path_wps_for_viz(start_pose, dest_poses)

    def get_route_length(self, start_pose, end_pose):
        return self.router.get_route_length(start_pose, end_pose)

    def get_route(self, start_pose, end_pose):
        return self.router.solve_route(start_pose, end_pose)


class AllRouterModules:
    def __init__(self, fleet_names):
        self.fleet_names = fleet_names
        self.router_modules = {}
        for fleet_name in self.fleet_names:
            self.add_router_module(fleet_name)

    @utils_util.report_error
    def get_router_module(self, fleet_name: str):
        rm = self.router_modules.get(fleet_name, None)
        if rm is None:
            raise Exception(f"Unable to get router module for {fleet_name}")
        return rm

    @utils_util.report_error
    def add_router_module(self, fleet_name):
        try:
            map_path = os.path.join(os.environ["FM_STATIC_DIR"], f"{fleet_name}/map/")
            self.router_modules.update({fleet_name: RouterModule(map_path)})
        except Exception as e:
            logging.error(
                f"Unable to create router module for fleet {fleet_name}, exception: {e}"
            )
