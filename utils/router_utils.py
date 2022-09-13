from mule.ati.control.bridge.router_planner_interface import RoutePlannerInterface


class RouterModule:
    router = RoutePlannerInterface().router()

    @classmethod
    def get_path_wps(cls, start_pose, dest_poses):
        return cls.router.generate_path_wps_for_viz(start_pose, dest_poses)

    @classmethod
    def get_route_length(cls, start_pose, end_pose):
        return cls.router.get_route_length(start_pose, end_pose)

    @classmethod
    def get_route(cls, start_pose, end_pose):
        return cls.router.solve_route(start_pose, end_pose)
