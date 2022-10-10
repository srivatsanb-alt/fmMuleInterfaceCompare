import numpy as np
from utils.router_utils import RouterModule
from core.config import Config
from models.db_session import DBSession
from models.fleet_models import Fleet, AvailableSherpas
from models.trip_models import Trip, PendingTrip, TripStatus
from typing import List
import datetime
from optimal_dispatch.hungarian import hungarian_assignment
import time
import os


class OptimalDispatch:
    def __init__(self, method: str):
        self.pickup_q = {}
        self.sherpa_q = {}
        self.assignment_method = method
        self.assign = getattr(self, self.assignment_method)
        self.last_assigment_time = {}
        self.fleet_names = Config.get_all_fleets()
        self.fleets: List[Fleet] = []
        self.router_utils = {}

        for fleet_name in self.fleet_name:
            self.last_assigment_time[fleet_name] = datetime.datetime.now()
            map_path = os.path.join(os.environ["FM_MAP_DIR"], f"{fleet_name}/map/")
            temp = RouterModule(map_path)
            self.router_utils.update({fleet_name: temp})

    def any_new_trips_booked(self, session, fleet_name):
        updates = (
            session.session.query(Trip)
            .filter(Trip.updated_at > self.last_assigment_time[fleet_name])
            .filter(Trip.status == TripStatus.BOOKED)
            .filter(Trip.fleet_name == fleet_name)
            .filter(Trip.start_time > datetime.datetime.now())
            .all()
        )
        if updates:
            return True
        return False

    def any_new_sherpa_available(self, session, fleet_name):
        updates = (
            session.session.query(AvailableSherpas)
            .filter(AvailableSherpas.updated_at > self.last_assigment_time[fleet_name])
            .filter(AvailableSherpas.fleet_name == fleet_name)
            .all()
        )
        if updates:
            return True
        return False

    def hungarian(self, cost_matrix, pickups, sherpas):
        return hungarian_assignment(cost_matrix, pickups, sherpas)

    def update_sherpa_q(self, dbsession, fleet_name):
        self.sherpa_q = {}
        available_sherpas = dbsession.session.get_all_available_sherpas(fleet_name)
        for available_sherpa_name in available_sherpas:
            available_sherpa = dbsession.session.get_sherpa(available_sherpa_name)
            trip_id = available_sherpas.sherpa.trip_id
            pose = available_sherpa.sherpa.status.pose
            remaining_eta = 0

            if trip_id:
                trip: Trip = dbsession.session.get_trip(trip_id)
                remaining_eta = [eta for eta in trip.etas if eta is not None]
                final_dest = trip.augumented_route[-1]
                final_pose = dbsession.session.get_station(final_dest).pose
                pose = final_pose

            self.sherpa_q.update(
                {
                    available_sherpa.sherpa_name: {
                        "pose": pose,
                        "remaining_eta": remaining_eta,
                    }
                }
            )

    def update_pickup_q(self, dbsession, fleet_name):
        self.pickup_q = {}
        pending_trips = (
            dbsession.session.query(PendingTrip)
            .join(PendingTrip.trip)
            .filter(Trip.fleet_name == fleet_name)
            .all()
        )

        for pending_trip in pending_trips:
            pose = dbsession.session.get_station(pending_trip.trip.route[0]).pose
            self.pickup_q.update({pending_trip.trip_id: {"pose": pose}})

    def assemble_cost_matrix(self, router_utils):
        cost_matrix = np.ones((len(self.pickup_q), len(self.sherpa_q))) * np.inf
        i = 0
        j = 0
        for pickup_keys, pickup_q_val in self.pickup_q.items():
            for sherpa_q, sherpa_q_val in self.sherpa_q.items():
                cost_matrix[i, j] = (
                    router_utils.get_route_length(
                        np.array(sherpa_q_val["pose"]), np.array(pickup_q_val["pose"])
                    )
                    + sherpa_q_val["remaining_eta"]
                )
                j += 1
            i += 1
        return cost_matrix

    def update_pending_trips(dbsession, assignments):

        for pickup, sherpa_name in assignments.items():
            ptrip = dbsession.session.get_pending_trip_with_trip_id(pickup)
            ptrip.sherpa_name = sherpa_name

        # commit all the changes
        dbsession.session.close()

    def run(self):
        time.sleep(5)
        with DBSession() as dbsession:
            self.fleets = dbsession.session.get_all_fleets()
            while True:
                for fleet in self.fleets:
                    if self.any_new_trips_booked(
                        dbsession, fleet.name
                    ) or self.any_new_sherpa_available(dbsession, fleet.name):

                        self.update_sherpa_q(dbsession, fleet.name)
                        self.update_pickup_q(dbsession, fleet.name)
                        router_utils = self.router_utils[fleet.name]
                        cost_matrix = self.assemble_cost_matrix(router_utils)
                        assignments = self.assign(
                            cost_matrix,
                            list(self.pickup_q.keys()),
                            list(self.sherpa_q.keys()),
                        )
                        self.update_pending_trips(dbsession, assignments)
                        self.last_assigment_time[fleet.name] = datetime.datetime.now()

                        dbsession.session.refresh(fleet)

                time.sleep(1)
