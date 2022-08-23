from mule.ati.control.bridge.router_planner_interface import RoutePlannerInterface


class RouterModule:
    router: None

    @classmethod
    def get_path_lines(cls, start_pose, dest_poses):
        if not cls.router:
            rpi = RoutePlannerInterface()
            cls.router = rpi.router
        return cls.router.generate_path_wps_for_viz(start_pose, dest_poses)
