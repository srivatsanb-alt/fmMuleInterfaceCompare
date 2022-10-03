from mule.ati.control.bridge.router_planner_interface import RoutePlannerInterface


class RouterModule:
    def __init__(self, gmaj_path=None):
        self.router = RoutePlannerInterface(gmaj_path).router()

    def get_path_wps(self, start_pose, dest_poses):
        return self.router.generate_path_wps_for_viz(start_pose, dest_poses)

    def get_route_length(self, start_pose, end_pose):
        return self.router.get_route_length(start_pose, end_pose)

    def get_route(self, start_pose, end_pose):
        return self.router.solve_route(start_pose, end_pose)
