import time
from utils.rq_utils import Queues, enqueue
from core.config import Config
from models.request_models import (
    SherpaStatusMsg,
    TripStatusMsg,
    TripInfo,
    Stoppages,
    StoppageInfo,
    SherpaReq,
    BookingReq,
    TripMsg,
)
from utils.router_utils import RouterModule, get_dense_path
from models.trip_models import OngoingTrip
from typing import List
import sys
import json
import os
import uvicorn
from multiprocessing import Process
import redis
import numpy as np
from models.db_session import DBSession
from models.fleet_models import Sherpa, Station
from models.request_models import ReachedReq
import threading


def should_trip_msg_be_sent(sherpa_events):
    reached_flag = False
    move_to_flag = False
    for s_event in sherpa_events:
        if s_event.msg_type == "move_to":
            move_to_flag = True
            reached_flag = False
        if s_event.msg_type == "reached":
            reached_flag = True

    return move_to_flag and not reached_flag


def handle(handler, msg):
    handler.handle(msg)


class MuleAPP:
    def __init__(self):
        self.sherpa_apps = []
        self.host_all_mule_app()

    def host_uvicorn(self, config):
        server = uvicorn.Server(config)
        server.run()

    def host_all_mule_app(self):
        self.kill_all_mule_app()
        with DBSession() as dbsession:
            all_sherpas = dbsession.get_all_sherpas()

            sys.path.append(os.environ["MULE_ROOT"])
            os.environ["ATI_SUB"] = "ipc:////app/out/zmq_sub"
            os.environ["ATI_PUB"] = "ipc:////app/out/zmq_sub"
            redis_db = redis.from_url(os.getenv("FM_REDIS_URI"))

            # mule looks for control_init to accept move_to req
            redis_db.set("control_init", json.dumps(True))

            from mule.ati.fastapi.mule_app import mule_app

            port = 5001
            for sherpa in all_sherpas:
                config = uvicorn.Config(mule_app, host="0.0.0.0", port=port, reload=True)
                sherpa.ip_address = "0.0.0.0"
                sherpa.port = str(port)
                self.sherpa_apps.append(
                    Process(target=self.host_uvicorn, args=[config], daemon=True)
                )
                self.sherpa_apps[-1].start()
                port = port + 1

    def kill_all_mule_app(self):
        with DBSession() as dbsession:
            all_sherpas = dbsession.get_all_sherpas()
            for sherpa in all_sherpas:
                sherpa.port = None
            for proc in self.sherpa_apps:
                proc.kill()


class FleetSimulator:
    def __init__(self):
        self.handler_obj = Config.get_handler()
        self.fleet_names = Config.get_all_fleets()
        self.simulator_config = Config.get_simulator_config()
        self.should_book_trips = self.simulator_config["book_trips"]
        self.router_modules = {}
        for fleet_name in self.fleet_names:
            map_path = os.path.join(os.environ["FM_MAP_DIR"], f"{fleet_name}/map")
            self.router_modules.update({fleet_name: RouterModule(map_path)})

    def initialize_sherpas(self):

        with DBSession() as dbsession:
            sherpas: List[Sherpa] = dbsession.get_all_sherpas()
            stations: List[Station] = dbsession.get_all_stations()

            for sherpa in sherpas:
                self.send_verify_fleet_files_req(sherpa.name)
                print(f"sending verify fleet files req sherpa: {sherpa.name}")

                time.sleep(5)

                for sherpa in sherpas:
                    station_fleet_name = None
                    while sherpa.fleet.name != station_fleet_name:
                        i = np.random.randint(0, len(stations))
                        station_fleet_name = stations[i].fleet.name

                    st = stations[i]
                    self.send_sherpa_status(sherpa.name, mode="fleet", pose=st.pose)

    def book_trip(self, route, freq):
        generic_q = Queues.queues_dict["generic_handler"]
        trip_msg = TripMsg(route=route)
        book_req = BookingReq(trips=[trip_msg], source="simulator")
        while True:
            enqueue(generic_q, handle, self.handler_obj, book_req)
            time.sleep(freq)

    def book_predefined_trips(self):
        all_route_details = self.simulator_config.get("routes", {})
        if self.should_book_trips:
            for route_name, route_detail in all_route_details.items():
                route = route_detail[0]
                freq = route_detail[1][0]
                print(f"will book trip with route {route} every {freq} seconds")
                t = threading.Thread(target=self.book_trip, args=[route, freq])
                t.daemon = True
                t.start()

    def send_verify_fleet_files_req(self, sherpa_name):
        generic_q = Queues.queues_dict["generic_handler"]
        msg = SherpaReq(
            type="verify_fleet_files", source=sherpa_name, timestamp=time.time()
        )
        enqueue(generic_q, handle, self.handler_obj, msg, ttl=1)

    def send_sherpa_status(self, sherpa_name, mode=None, pose=None, battery_status=None):
        with DBSession() as session:
            sherpa_update_q = Queues.queues_dict[f"{sherpa_name}_update_handler"]

            sherpa: Sherpa = session.get_sherpa(sherpa_name)

            msg = {}
            msg["type"] = "sherpa_status"
            msg["source"] = sherpa_name
            msg["sherpa_name"] = sherpa_name
            msg["timestamp"] = time.time()
            msg["mode"] = mode if mode else "fleet"
            msg["current_pose"] = sherpa.status.pose if not pose else pose
            msg["battery_status"] = -1 if not battery_status else battery_status
            # print(f"will send a proxy sherpa status {msg}")

            if sherpa.status.pose or pose:
                msg = SherpaStatusMsg.from_dict(msg)
                enqueue(sherpa_update_q, handle, self.handler_obj, msg, ttl=1)

    def send_trip_status(self, sherpa_name):

        with DBSession() as session:
            sherpa_trip_q = Queues.queues_dict[f"{sherpa_name}_trip_update_handler"]

            ongoing_trip: OngoingTrip = session.get_ongoing_trip(sherpa_name)
            sherpa: Sherpa = session.get_sherpa(sherpa_name)
            from_station = ongoing_trip.trip_leg.from_station
            to_station = ongoing_trip.trip_leg.to_station

            if from_station:
                from_pose = session.get_station(from_station).pose
            else:
                from_pose = sherpa.status.pose

            to_pose = session.get_station(to_station).pose
            rm = self.router_modules[sherpa.fleet.name]

            if to_pose == from_pose:
                self.send_reached_msg(sherpa_name)
                print(f"ending trip leg {from_station}, {to_station}")
                return

            final_route = rm.get_route(from_pose, to_pose)[0]
            eta_at_start = rm.get_route_length(from_pose, to_pose)
            x_vals, y_vals, t_vals, _ = get_dense_path(final_route)
            # sleep_time = 1
            steps = 1000
            sleep_time = steps * (eta_at_start / len(x_vals))
            print(
                f"{sherpa.name}, trip_leg_id: {ongoing_trip.trip_leg_id} sleep time {sleep_time}"
            )
            for i in range(0, len(x_vals), steps):
                sherpa: Sherpa = session.get_sherpa(sherpa_name)
                session.session.refresh(sherpa)
                if not sherpa.status.trip_id:
                    print(
                        f"ending trip leg {from_station}, {to_station}, seems like trip was deleted"
                    )
                    return

                stoppage_type = ""
                local_obstacle = [-999.0, -999.0]

                obst_random = np.random.rand(1)[0]
                if obst_random < 0.07:
                    stoppage_type = "Stopped due to detected obstacle"
                    local_obstacle = [0.1, 1]

                curr_pose = [x_vals[i], y_vals[i], t_vals[i]]

                if i % 50 == 0:
                    print(
                        f"simulating trip_id: {ongoing_trip.trip_id}, progress: {i / len(x_vals)}"
                    )

                self.send_sherpa_status(sherpa.name, mode="fleet", pose=curr_pose)
                eta = ((len(x_vals) - i) / len(x_vals)) * eta_at_start
                trip_status_msg = {
                    "type": "trip_status",
                    "timestamp": time.time(),
                    "trip_id": ongoing_trip.trip_id,
                    "trip_leg_id": ongoing_trip.trip_leg_id,
                    "trip_info": {
                        "current_pose": curr_pose,
                        "destination_pose": to_pose,
                        "destination_name": ongoing_trip.trip_leg.to_station,
                        "total_route_length": eta_at_start,
                        "remaining_route_length": eta,
                        "eta_at_start": eta_at_start,
                        "eta": eta,
                        "cte": 0.0,
                        "te": 0.0,
                        "progress": i / len(x_vals),
                    },
                    "stoppages": {
                        "type": stoppage_type,
                        "extra_info": {
                            "local_obstacle": local_obstacle,
                            "velocity_speed_factor": 1.0,
                            "obstacle_speed_factor": 1.0,
                            "time_elapsed_stoppages": 0,
                            "time_elapsed_obstacle_stoppages": 0,
                            "time_elapsed_visa_stoppages": 0,
                            "time_elapsed_other_stoppages": 0,
                        },
                    },
                }

                trip_status_msg["source"] = sherpa.name
                final_trip_status_msg = TripStatusMsg.from_dict(trip_status_msg)
                final_trip_status_msg.trip_info = TripInfo.from_dict(
                    trip_status_msg["trip_info"]
                )
                final_trip_status_msg.stoppages = Stoppages.from_dict(
                    trip_status_msg["stoppages"]
                )
                final_trip_status_msg.stoppages.extra_info = StoppageInfo.from_dict(
                    trip_status_msg["stoppages"]["extra_info"]
                )
                print("sending trip status")
                enqueue(
                    sherpa_trip_q,
                    handle,
                    self.handler_obj,
                    final_trip_status_msg,
                    ttl=1,
                )
                time.sleep(sleep_time)

            dest_pose = [x_vals[-1], y_vals[-1], t_vals[-1]]
            self.send_sherpa_status(sherpa.name, mode="fleet", pose=dest_pose)
            self.send_reached_msg(sherpa_name)
            print(f"ending trip leg {from_station}, {to_station}")

    def send_reached_msg(self, sherpa_name):
        queue = Queues.queues_dict["generic_handler"]

        with DBSession() as dbsession:
            ongoing_trip: OngoingTrip = dbsession.get_ongoing_trip(sherpa_name)
            st_pose = dbsession.get_station(ongoing_trip.trip_leg.to_station).pose
            reached_req = ReachedReq(
                timestamp=time.time(),
                trip_id=ongoing_trip.trip_id,
                trip_leg_id=ongoing_trip.trip_leg_id,
                destination_pose=st_pose,
                destination_name=ongoing_trip.trip_leg.to_station,
            )
            reached_req.source = sherpa_name
            print(f"will send a reached msg for {sherpa_name}, {reached_req}")
            enqueue(queue, handle, self.handler_obj, reached_req, ttl=1)

    def act_on_sherpa_events(self):
        simulated_trip_legs = []
        active_threads = {}
        print("Will act on sherpa events")
        with DBSession() as dbsession:
            while True:
                sherpas = dbsession.get_all_sherpas()
                for sherpa in sherpas:
                    dbsession.session.refresh(sherpa)
                    trip_leg = dbsession.get_trip_leg(sherpa.name)
                    if trip_leg:
                        if trip_leg.id not in simulated_trip_legs:
                            print(
                                f"starting trip simulation for sherpa {sherpa.name}, trip_leg: {trip_leg.__dict__}"
                            )
                            t = threading.Thread(
                                target=self.send_trip_status, args=[sherpa.name]
                            )
                            t.daemon = True
                            t.start()
                            simulated_trip_legs.append(trip_leg.id)
                            active_threads[sherpa.name] = t
                        else:
                            if not active_threads.get(sherpa.name).is_alive():
                                self.send_sherpa_status(sherpa.name)
                    else:
                        print(f"no trip_leg for {sherpa.name}")
                        self.send_sherpa_status(sherpa.name)

                    if sherpa.status.disabled:
                        print(f"{sherpa.name} disabled: {sherpa.status.disabled_reason}")

                time.sleep(1)
