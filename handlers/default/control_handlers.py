from utils.router_utils import RouterModule
from models.request_models import GiveRouteWPS

router: RouterModule = RouterModule()


class ControlHandlers:
    def give_route_wps(self, wps_req: GiveRouteWPS):
        return router.get_path_wps(wps_req.start_pose, wps_req.to_poses)
