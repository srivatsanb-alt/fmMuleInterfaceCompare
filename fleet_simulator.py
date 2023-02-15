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
    VisaReq,
    ResourceReq,
)
from utils.router_utils import RouterModule, get_dense_path
from models.trip_models import OngoingTrip
import models.trip_models as tm
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
from models.request_models import ReachedReq, DispatchButtonReq, SherpaPeripheralsReq
import threading

LOOKAHEAD = 5.0
PATH_DENSITY = 1000
THETA_MAX = np.rad2deg(10)


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


def find_gate_params(ez, name):
    for zid, zone_details in ez.items():
        if zone_details["name"] == name:
            return zone_details


def read_ez_files(ez_file):
    with open(ez_file, "r") as f:
        ez_dict = json.load(f)
    exc_zones = ez_dict["ez_gates"]
    # zone_ids = list(ezones.keys())
    # zones_list = []
    # for zone in ezones.values():
    #    zones_list.append(zone)
    # exc_zones = get_zone_dict(zones_list, zone_ids)
    return exc_zones


def entry_exit_zone_check(pose, gate_params, enter=True):
    c_t, s_t = gate_params["opening_direction"]
    x, y, _ = pose
    q1 = np.array([x, y])
    p1, p2 = gate_params["line_segment"]
    if enter:
        visa_lookahead = gate_params["apply_dist"]
        xv, yv = x + visa_lookahead * c_t, y + visa_lookahead * s_t
    else:
        # release_distance = gate_params['transit_visa_release_dist']
        release_distance = 4.0
        xv, yv = x - release_distance * c_t, y - release_distance * s_t
    q2 = np.array([xv, yv])
    return intersection_check(np.array(p1), np.array(p2), q1, q2)


def check_visa_release(ez, pose, visas_held):
    print(f"visa held {visas_held}")
    print(f"exclusion zone {ez}")
    gate_params = find_gate_params(ez, visas_held)
    print(f"gate params {gate_params}")
    if not entry_exit_zone_check(pose, gate_params, enter=False):
        return visas_held, gate_params["name"]
    return None


def check_visa_needed(ez, pose):
    x, y, theta = pose
    q1 = np.asarray([x, y])
    for zoi, gate_params in ez.items():
        approaching_zone = entry_exit_zone_check(pose, gate_params)
        if approaching_zone:  # Entering visa zone
            return zoi, gate_params["name"]
    return None


def wedge(a, b):
    return a[0] * b[1] - a[1] * b[0]


def intersection_check(p, p2, q, q2):
    u, v, d = p2 - p, q2 - q, p - q
    w = wedge(v, u)
    if w != 0:
        t1 = wedge(d, v) / w
        t2 = wedge(d, u) / w
        if (0 <= t1 <= 1) and (0 <= t2 <= 1):
            return True
    return False


def find_next_pose_index(traj, idx, dmax):
    x, y, t = traj
    traj_length = len(x)
    wmin, wmax = idx, np.minimum(idx + int(LOOKAHEAD * PATH_DENSITY), traj_length)
    i = wmin + 1
    d = 0.0
    theta = 0.0
    while i < wmax and d < dmax and theta < THETA_MAX:
        d += np.sqrt((x[i] - x[i - 1]) ** 2 + (y[i] - y[i - 1]) ** 2)
        theta += np.abs(t[i] - t[i - 1])
        i += 1
    return i - wmin


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
        with DBSession() as dbsession:
            self.fleet_names = dbsession.get_all_fleet_names()
        self.simulator_config = Config.get_simulator_config()
        self.should_book_trips = self.simulator_config.get("book_trips", False)
        self.router_modules = {}
        self.exclusion_zones = {}
        self.visas_held = {}
        self.visa_needed = {}
        self.visa_handling = {}
        print(f"simulator config {self.simulator_config}")
        self.pause_at_station = self.simulator_config.get("pause_at_station", 10.0)
        self.sim_speedup_factor = self.simulator_config.get("speedup_factor", 1.0)
        self.avg_velocity = self.simulator_config.get("average_velocity", 0.8)
        self.initialize_sherpas_at = self.simulator_config.get("initialize_sherpas_at")
        for fleet_name in self.fleet_names:
            map_path = os.path.join(os.environ["FM_MAP_DIR"], f"{fleet_name}/map")
            ez_path = os.path.join(map_path, "ez.json")
            try:
                self.exclusion_zones.update({fleet_name: read_ez_files(ez_path)})
                self.visa_handling[fleet_name] = self.simulator_config["visa_handling"]
            except:
                self.visa_handling[fleet_name] = False
            print(
                f"Visa handling {self.visa_handling} Exclusion zones... {self.exclusion_zones}"
            )
            self.router_modules.update({fleet_name: RouterModule(map_path)})

    def initialize_sherpas(self):

        with DBSession() as dbsession:
            sherpas: List[Sherpa] = dbsession.get_all_sherpas()
            stations: List[Station] = dbsession.get_all_stations()

            for sherpa in sherpas:
                self.send_verify_fleet_files_req(sherpa.name)
                print(f"sending verify fleet files req sherpa: {sherpa.name}")
                self.visas_held[sherpa.name] = []
                self.visa_needed[sherpa.name] = []

                time.sleep(5)

                for sherpa in sherpas:
                    station_fleet_name = None
                    station_name = self.initialize_sherpas_at.get(sherpa.name)
                    print(f"Initializing sherpa {sherpa.name} station_name {station_name}")
                    try:
                        st = dbsession.get_station(station_name)
                    except:
                        st = None
                    station_fleet_name = st.fleet.name if st else None
                    print(
                        f"sherpa fleet {sherpa.fleet.name} station_fleet_name {station_fleet_name}"
                    )
                    while sherpa.fleet.name != station_fleet_name:
                        i = np.random.randint(0, len(stations))
                        station_fleet_name = stations[i].fleet.name
                        st = stations[i]
                        print("Randomizing the start station")
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

    def get_visa_request(self, sherpa_name, visa_params):
        zone_id, zone_name = visa_params
        visa_details = {"zone_id": zone_id, "zone_name": zone_name, "visa_type": "transit"}
        visa_request_msg = {
            "type": "resource_access",
            "access_type": "request",
            "visa": VisaReq(**visa_details),
            "to_fm": True,
            "timestamp": time.time(),
            "source": sherpa_name,
        }
        return ResourceReq(**visa_request_msg)

    def get_visa_release(self, sherpa_name, visa_params):
        zone_id, zone_name = visa_params
        visa_details = {"zone_id": zone_id, "zone_name": zone_name, "visa_type": "transit"}
        visa_release_msg = {
            "type": "resource_access",
            "access_type": "release",
            "visa": VisaReq(**visa_details),
            "to_fm": True,
            "timestamp": time.time(),
            "source": sherpa_name,
        }
        return ResourceReq(**visa_release_msg)

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
            sherpa_visa_q = Queues.queues_dict["resource_handler"]
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

            final_route, _, route_length = rm.get_route(from_pose, to_pose)
            eta_at_start = rm.get_route_length(from_pose, to_pose)
            x_vals, y_vals, t_vals, _ = get_dense_path(final_route)
            traj = x_vals, y_vals, t_vals
            # sleep_time = 1
            steps = 1000
            sleep_time = self.sim_speedup_factor
            print(
                f"{sherpa.name}, trip_leg_id: {ongoing_trip.trip_leg_id} Pause_at_station: {self.pause_at_station}"
            )
            i = 0
            blocked_for_visa = False
            while i < len(x_vals):
                sherpa: Sherpa = session.get_sherpa(sherpa_name)
                session.session.refresh(sherpa)
                if not sherpa.status.trip_id:
                    print(
                        f"ending trip leg {from_station}, {to_station}, seems like trip was deleted"
                    )
                    return

                stoppage_type = ""
                local_obstacle = [-999.0, -999.0]
                curr_pose = [x_vals[i], y_vals[i], t_vals[i]]
                steps = find_next_pose_index(traj, i, self.avg_velocity * sleep_time)
                if i + steps >= len(x_vals):
                    break
                if (
                    len(self.visa_needed[sherpa_name]) == 0
                    or len(self.visas_held[sherpa_name]) > 0
                ):
                    i += steps
                    blocked_for_visa = False
                else:
                    print(f"Sherpa {sherpa_name} is waiting for a visa")
                    stoppage_type = "Waiting for visa"
                    blocked_for_visa = True
                # obst_random = np.random.rand(1)[0]
                # if obst_random < 0.07:
                #    stoppage_type = "Stopped due to detected obstacle"
                #    local_obstacle = [0.1, 1]

                if self.visa_handling[sherpa.fleet.name]:
                    ez = self.exclusion_zones[sherpa.fleet.name]
                    sherpa_visa = session.get_visa_held(sherpa_name)
                    print(f"visa held: {sherpa_visa}")
                    if len(sherpa_visa) > 0:
                        print(f"visa held: {sherpa_visa}")
                        zone_id = sherpa_visa[0].zone_id.rsplit("_", 1)[0]
                        print(f"VISA HELD for zone id: {zone_id}")
                        self.visas_held[sherpa_name] = sherpa_visa
                        self.visa_needed[sherpa_name] = []
                        visa_params = check_visa_release(ez, curr_pose, zone_id)
                        if visa_params is not None:
                            print(f"Visa released: {self.visas_held[sherpa_name]}")
                            visa_release_msg = self.get_visa_release(
                                sherpa_name, visa_params
                            )
                            enqueue(
                                sherpa_visa_q, handle, self.handler_obj, visa_release_msg
                            )
                            self.visas_held[sherpa_name] = []
                    else:
                        visa_params = check_visa_needed(ez, curr_pose)
                        print(f"Is Visa needed? {visa_params}")
                        if visa_params is not None:
                            self.visa_needed[sherpa_name] = visa_params[0]
                        if len(self.visa_needed[sherpa_name]) > 0:
                            print(
                                f"Visa for zone: {self.visa_needed[sherpa_name]}, needed for {sherpa_name}"
                            )
                            visa_request_msg = self.get_visa_request(
                                sherpa_name, visa_params
                            )
                            enqueue(
                                sherpa_visa_q, handle, self.handler_obj, visa_request_msg
                            )

                print(
                    f"simulating trip_id: {ongoing_trip.trip_id}, steps: {steps}, progress: {i / len(x_vals)}"
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
                            "obstacle_speed_factor": int(blocked_for_visa),
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
            time.sleep(self.pause_at_station)

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

    def simulate_peripherals(self, ongoing_trip):
        if ongoing_trip:
            states, sherpa_name = ongoing_trip.states, ongoing_trip.sherpa_name
            peripheral_response = SherpaPeripheralsReq(timestamp=time.time())
            peripheral_response.source = sherpa_name
            if (
                tm.TripState.WAITING_STATION_DISPATCH_START in states
                and tm.TripState.WAITING_STATION_DISPATCH_END not in states
            ):
                print(
                    f"Sherpa {sherpa_name} - trip_id {ongoing_trip.trip_id}, leg {ongoing_trip.trip_leg_id} is waiting for dispacth"
                )
                peripheral_response.dispatch_button = DispatchButtonReq(value=True)
            queue = Queues.queues_dict["generic_handler"]
            print(f"peripheral response msg {peripheral_response}")
            enqueue(queue, handle, self.handler_obj, peripheral_response, ttl=1)

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
                    ongoing_trip: OngoingTrip = dbsession.get_ongoing_trip(sherpa.name)
                    # self.simulate_peripherals(ongoing_trip)
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
