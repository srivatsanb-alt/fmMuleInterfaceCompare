import numpy as np
from core.logs import get_logger
from core.config import Config
from models.fleet_models import Fleet, AvailableSherpas
from models.trip_models import Trip, PendingTrip, TripStatus
from typing import List
from sqlalchemy.sql import or_
import datetime
from optimal_dispatch.hungarian import hungarian_assignment
import pandas as pd
from utils.util import are_poses_close


class OptimalDispatch:
    def __init__(self, method: str):
        self.logger = None
        self.pickup_q = {}
        self.sherpa_q = {}
        self.assignment_method = method
        self.assign = getattr(self, self.assignment_method)
        self.last_assigment_time = {}
        self.fleet_names = Config.get_all_fleets()
        self.fleets: List[Fleet] = []
        self.router_utils = {}
        self.ptrip_first_station = []
        for fleet_name in self.fleet_names:
            self.last_assigment_time[fleet_name] = datetime.datetime.now()

    def any_new_trips_booked(self, dbsession, fleet_name):

        updates = (
            dbsession.session.query(Trip)
            .filter(Trip.status == TripStatus.BOOKED)
            .filter(Trip.fleet_name == fleet_name)
            .filter(or_(Trip.start_time < datetime.datetime.now(), Trip.start_time == None))
            .all()
        )
        if updates:
            return True
        return False

    def any_trips_cancelled(self, dbsession, fleet_name):
        updates = (
            dbsession.session.query(Trip)
            .filter(Trip.updated_at > self.last_assigment_time)
            .fiter(Trip.status == TripStatus.CANCELLED)
            .all()
        )
        if updates:
            return True
        return False

    def any_change_in_sherpa_availability(self, dbsession, fleet_name):
        updates = (
            dbsession.session.query(AvailableSherpas)
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
        available_sherpas = dbsession.get_all_available_sherpa_names(fleet_name)
        for available_sherpa_name in available_sherpas:
            available_sherpa = dbsession.get_sherpa(available_sherpa_name)
            trip_id = available_sherpa.status.trip_id
            pose = available_sherpa.status.pose
            remaining_eta = 0

            if trip_id:
                trip: Trip = dbsession.get_trip(trip_id)
                remaining_eta = np.sum(trip.etas)
                final_dest = trip.augumented_route[-1]
                final_pose = dbsession.get_station(final_dest).pose
                pose = final_pose

            if not pose:
                raise ValueError(
                    f"{available_sherpa_name} pose is None, cannot assemble_cost_matrix"
                )

            # sherpas with pending trips can't be assigned anotther pending trip
            if available_sherpa.name not in dbsession.get_sherpas_with_pending_trip():
                self.sherpa_q.update(
                    {
                        available_sherpa.name: {
                            "pose": pose,
                            "remaining_eta": remaining_eta,
                        }
                    }
                )

    def update_pickup_q(self, dbsession, fleet_name):
        self.pickup_q = {}
        self.ptrip_first_station = []

        pending_trips = (
            dbsession.session.query(PendingTrip)
            .join(PendingTrip.trip)
            .filter(Trip.fleet_name == fleet_name)
            .all()
        )

        for pending_trip in pending_trips:
            pose = dbsession.get_station(pending_trip.trip.route[0]).pose
            if not pose:
                raise ValueError(
                    f"{pending_trip.trip.route[0]} pose is None,  cannot assemble_cost_matrix"
                )

            self.pickup_q.update({pending_trip.trip_id: {"pose": pose}})
            self.ptrip_first_station.append(pending_trip.trip.route[0])

    def assemble_cost_matrix(self, router_utils):
        cost_matrix = np.ones((len(self.pickup_q), len(self.sherpa_q))) * np.inf
        i = 0
        j = 0
        for pickup_keys, pickup_q_val in self.pickup_q.items():
            for sherpa_q, sherpa_q_val in self.sherpa_q.items():
                route_length = 0
                if not are_poses_close(sherpa_q_val["pose"], pickup_q_val["pose"]):
                    route_length = router_utils.get_route_length(
                        np.array(sherpa_q_val["pose"]), np.array(pickup_q_val["pose"])
                    )
                cost_matrix[i, j] = route_length + sherpa_q_val["remaining_eta"]
                j += 1
            i += 1

        return cost_matrix

    def update_pending_trips(self, dbsession, assignments):

        for pickup, sherpa_name in assignments.items():
            ptrip: PendingTrip = dbsession.get_pending_trip_with_trip_id(pickup)
            ptrip.sherpa_name = sherpa_name

            trip: Trip = dbsession.get_trip(pickup)
            trip.status = TripStatus.ASSIGNED

        # commit all the changes

    def run(self, dbsession, router_utils):
        self.router_utils = router_utils
        self.logger = get_logger("optimal_dispatch")
        self.logger.info("will run optimal dispatch logic")
        self.fleets = dbsession.get_all_fleets()

        for fleet in self.fleets:
            if (
                self.any_new_trips_booked(dbsession, fleet.name)
                or self.any_change_in_sherpa_availability(dbsession, fleet.name)
                or self.any_trips_cancelled(dbsession, fleet.name)
            ):

                self.logger.info(f"need to create/update assignments for {fleet.name}")
                self.update_sherpa_q(dbsession, fleet.name)
                self.logger.info(f"updated sherpa_q {self.sherpa_q}")

                self.update_pickup_q(dbsession, fleet.name)
                self.logger.info(f"updated pickup_q {self.pickup_q}")

                router_utils = self.router_utils[fleet.name]
                cost_matrix = self.assemble_cost_matrix(router_utils)

                pickup_list = list(self.pickup_q.keys())
                sherpa_list = list(self.sherpa_q.keys())

                cost_matrix_df = pd.DataFrame(
                    cost_matrix, index=self.ptrip_first_station, columns=sherpa_list
                )

                self.logger.info(
                    f"Assembled Cost Matrix for {fleet.name}:\n{cost_matrix_df}\n"
                )

                assignments = self.assign(
                    cost_matrix,
                    pickup_list,
                    sherpa_list,
                )

                self.logger.info(f"Assignments- {fleet.name}:\n")
                for i in range(0, len(assignments)):
                    self.logger.info(
                        f"{list(assignments.values())[i]} ---> {self.ptrip_first_station[i]}, trip_id: {list(assignments.keys())[i]}"
                    )
                self.logger.info("\n")

                self.update_pending_trips(dbsession, assignments)
                self.last_assigment_time[fleet.name] = datetime.datetime.now()
            else:
                self.logger.info(f"need not update assignment for {fleet.name}")
