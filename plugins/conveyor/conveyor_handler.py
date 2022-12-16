import sys
import logging
from dataclasses import dataclass
import redis
from .conveyor_utils import ConvInfo, session, ConvTrips
from plugins.plugin_comms import send_req_to_FM
from models.base_models import JsonMixin


@dataclass
class ToteStatus(JsonMixin):
    num_totes: int
    compact_time: int
    type: str
    name: str = None


class ConveyorDispatch:
    def __init__(self, optimal_dispatch_config: dict):
        self.fleet_names = Config.get_all_fleets()
        self.chutes = Config.get_all_chutes()
        self.fleets: List[Fleet] = []

    def get_nearest_chute(self, conveyor_pose, fleet_name):
        min_route_length = np.inf
        redis_conn = redis.from_url(os.getenv("FM_REDIS_URI"))
        for chute in self.chutes.items():
            pose_1 = conveyor_pose
            pose_2 = chute["pose"]
            job_id = generate_random_job_id()
            control_router_job = [pose_1, pose_2, fleet_name, job_id]
            redis_conn.set(f"control_router_job_{job_id}", json.dumps(control_router_job))
            while not redis_conn.get(f"result_{job_id}"):
                time.sleep(0.005)

            route_length = json.loads(redis_conn.get(f"result_{job_id}"))
            redis_conn.delete(f"result_{job_id}")
            if route_length < min_route_length:
                min_route_length = route_length
                nearest_chute = chute

        return nearest_chute


class CONV_HANDLER:
    def init_handler(self):
        self.plugin_name = "plugin_conveyor"

    def close_db(self):
        session.commit()
        session.close()

    def handle_tote_status(self, msg: dict):
        self.logger.info("Handling tote_status:")
        tote_status = ToteStatus.from_dict(msg)
        logging.info(f"conveyor name: {tote_status.name}")
        conv_info: ConvInfo = (
            session.query(ConvInfo).filter(ConvInfo.name == tote_status.name).one_or_none()
        )
        logging.info(f"conv_info:{conv_info}")
        if conv_info is not None:
            if tote_status.num_totes > conv_info.num_totes:
                route = []
                route.append(conv_info.name)
                if conv_info.nearest_chute:
                    route.append(conv_info.nearest_chute)
                else:
                    dispatcher = ConveyorDispatch()
                    nearest_chute = dispatcher.get_nearest_chute(
                        ConvInfo.pose, ConvInfo.fleet_name
                    )
                    route.append(nearest_chute)
                num_units = min(2, msg["num_totes"] - conv_info.num_totes)
                # book trip only when compacting time is -ve!
                req_json = {
                    "trips": [
                        {
                            "route": route,
                            "priority": 1,
                            "metadata": {"conveyor_ops": {"num_units": num_units}},
                        }
                    ]
                }

                endpoint = "trip_book"
                self.logger.info(
                    f"Sending req to FM with num_units: {num_units}, route: {route}"
                )
                status_code, response_json = send_req_to_FM(
                    self.plugin_name, endpoint, req_type="post", req_json=req_json
                )
                if response_json is not None:
                    for trip_id, trip_details in response_json.items():
                        trip = ConvTrips(
                            booking_id=trip_details["booking_id"],
                            trip_id=trip_id,
                            route=route,
                            trip_metadata=req_json["trips"][0]["metadata"],
                        )
                        session.add(trip)
            else:
                logging.info(
                    f"Num totes on conveyor ({tote_status.num_totes}) not greater than db info ({conv_info.num_totes})."
                )
        else:
            logging.info(f"No conveyor named {msg['name']} in gmaj!")
        conv_info.num_totes = tote_status.num_totes

    def handle(self, msg):
        self.logger = logging.getLogger("plugin_conveyor")
        self.logger.info(f"got a message {msg}")
        self.init_handler()
        msg_type = msg["type"]
        fn_handler = getattr(self, f"handle_{msg_type}", None)
        if not fn_handler:
            self.logger.info(f"Cannot handle msg, {msg}")
            return
        msg["name"] = msg["unique_id"]
        fn_handler(msg)
        self.close_db()
