import numpy as np
import logging
import logging.config
import redis
from typing import List
from sqlalchemy.sql import or_
import os
import datetime
import pandas as pd

# ati code imports
import utils.log_utils as lu
import utils.util as utils_util
from core.constants import FleetStatus
from models.fleet_models import Fleet, AvailableSherpas, OptimalDispatchState
from models.trip_models import Trip, PendingTrip, TripStatus
from optimal_dispatch.hungarian import hungarian_assignment

# get log config
logging.config.dictConfig(lu.get_log_config_dict())


# as per the bookings of trips, and their priorities, optimal dispatch will assign trips to the sherpas
# while ensuring the bookings and trips are valid(eg.start time of the trip should be greater than
# or equal to the current time)


class OptimalDispatch:
    def __init__(self, optimal_dispatch_config: dict):
        self.logger = None
        self.pickup_q = {}
        self.sherpa_q = {}
        self.config = optimal_dispatch_config
        self.assignment_method = self.config["method"]
        self.assign = getattr(self, self.assignment_method)
        self.fleet_names = []
        self.fleets: List[Fleet] = []
        self.router_utils = {}
        self.ptrip_first_station = []

    def get_exclude_stations_for_sherpa(self, dbsession, sherpa_name):
        saved_route = dbsession.get_saved_route(f"exclude_stations_{sherpa_name}")
        if saved_route is None:
            route = []
        else:
            route = saved_route.route

        return route

    def get_last_assignment_time(self, dbsession):
        self.last_assignment_time = {}
        all_last_assignment_data = dbsession.session.query(OptimalDispatchState).all()
        for last_assignment_data in all_last_assignment_data:

            if last_assignment_data.last_assignment_time is not None:
                self.last_assignment_time[
                    last_assignment_data.fleet_name
                ] = last_assignment_data.last_assignment_time
            else:
                self.last_assignment_time[
                    last_assignment_data.fleet_name
                ] = datetime.datetime.now()

    def update_last_assignment_time(self, dbsession, fleet_name):
        fleet_last_assignment_data = (
            dbsession.session.query(OptimalDispatchState)
            .filter(OptimalDispatchState.fleet_name == fleet_name)
            .one()
        )
        fleet_last_assignment_data.last_assignment_time = datetime.datetime.now()

    def are_power_factors_valid(self):
        w1 = self.config["eta_power_factor"]
        w2 = self.config["priority_power_factor"]

        if 0 <= w1 <= 1 and 0 <= w2 <= 1:
            return True

        raise ValueError("power factors are not valid, need to be in the range of 0-1")

    def all_data_available(self, dbsession, fleet_name):
        available_sherpas = dbsession.get_all_available_sherpa_names(fleet_name)
        for available_sherpa_name in available_sherpas:
            available_sherpa = dbsession.get_sherpa(available_sherpa_name)
            pose = available_sherpa.status.pose
            if pose is None:
                return False
        return True

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
            .filter(Trip.updated_at > self.last_assignment_time[fleet_name])
            .filter(Trip.fleet_name == fleet_name)
            .filter(Trip.status == TripStatus.CANCELLED)
            .all()
        )
        if updates:
            return True
        return False

    def any_change_in_sherpa_availability(self, dbsession, fleet_name):
        updates = (
            dbsession.session.query(AvailableSherpas)
            .filter(AvailableSherpas.updated_at > self.last_assignment_time[fleet_name])
            .filter(AvailableSherpas.fleet_name == fleet_name)
            .all()
        )
        if updates:
            return True
        return False

    def get_waiting_time_priorities(self, pending_trips):
        waiting_times = []
        for pending_trip in pending_trips:
            wait_time_dt = datetime.datetime.now() - pending_trip.trip.booking_time

            if pending_trip.trip.scheduled:
                trip_metadata = pending_trip.trip.trip_metadata
                scheduled_start_time = utils_util.str_to_dt(
                    trip_metadata["scheduled_start_time"]
                )
                wait_time_dt = datetime.datetime.now() - scheduled_start_time

            waiting_times.append(wait_time_dt.seconds)

        if waiting_times:
            waiting_time_priorities = np.array(waiting_times)

            # priority cannot be zero
            waiting_time_priorities[waiting_time_priorities <= 0] = 1

            min_wait_time = np.min(waiting_time_priorities)
            waiting_time_priorities = waiting_time_priorities / min_wait_time
            return waiting_time_priorities

        return [1] * len(pending_trips)

    def hungarian(self, cost_matrix, pickups, sherpas):
        return hungarian_assignment(cost_matrix, pickups, sherpas)

    def update_sherpa_q(self, dbsession, fleet_name):
        self.sherpa_q = {}
        available_sherpas = dbsession.get_all_available_sherpa_names(fleet_name)
        for available_sherpa_name in available_sherpas:
            available_sherpa = dbsession.get_sherpa(available_sherpa_name)
            trip_id = available_sherpa.status.trip_id
            pose = available_sherpa.status.pose
            parking_mode = False
            if available_sherpa.status.other_info is not None:
                parking_mode = available_sherpa.status.other_info.get("parking_mode", False)
            remaining_eta = 0

            if trip_id:
                trip: Trip = dbsession.get_trip(trip_id)
                remaining_eta = np.sum(trip.etas)
                final_dest = trip.augmented_route[-1]
                try:
                    final_pose = dbsession.get_station(final_dest).pose
                except Exception as e:
                    raise Exception(
                        f"Unable to get pose, details of station: {final_dest}, exception: {e}"
                    )

                pose = final_pose

            if not pose:
                raise ValueError(
                    f"{available_sherpa_name} pose is None, cannot assemble_cost_matrix"
                )

            # sherpas with pending trips can't be assigned anotther pending trip
            # if available_sherpa.name not in dbsession.get_sherpas_with_pending_trip():
            self.sherpa_q.update(
                {
                    available_sherpa.name: {
                        "pose": pose,
                        "remaining_eta": remaining_eta,
                        "exclude_stations": self.get_exclude_stations_for_sherpa(
                            dbsession, available_sherpa.name
                        ),
                        "fleet_status": available_sherpa.fleet.status,
                        "parking_mode": parking_mode,
                    }
                }
            )

    def get_valid_pending_trips(self, pending_trips):
        valid_pending_trips = []
        for pending_trip in pending_trips:
            if pending_trip.trip.scheduled:
                trip_metadata = pending_trip.trip.trip_metadata
                scheduled_start_time = utils_util.str_to_dt(
                    trip_metadata["scheduled_start_time"]
                )
                if scheduled_start_time > datetime.datetime.now():
                    continue
            valid_pending_trips.append(pending_trip)

        return valid_pending_trips

    def update_pickup_q(self, dbsession, fleet_name):
        self.pickup_q = {}
        self.ptrip_first_station = []

        pending_trips = dbsession.get_pending_trips_with_fleet_name(fleet_name)
        pending_trips = self.get_valid_pending_trips(pending_trips)

        waiting_time_priorities = [1] * len(pending_trips)
        if self.config.get("prioritise_waiting_stations", True):
            waiting_time_priorities = self.get_waiting_time_priorities(pending_trips)
            self.logger.info(f"waiting_time_priorities : {waiting_time_priorities}")

        count = 0

        for pending_trip in pending_trips:
            pending_trip.sherpa_name = None
            pending_trip.trip.sherpa_name = None
            pending_trip.trip.status = TripStatus.BOOKED
            trip_metadata = pending_trip.trip.trip_metadata

            sherpa_name = None
            if trip_metadata is not None:
                sherpa_name = trip_metadata.get("sherpa_name")

            try:
                pose = dbsession.get_station(pending_trip.trip.route[0]).pose
            except Exception as e:
                raise Exception(
                    f"Unable to get pose, details of station: {pending_trip.trip.route[0]}, exception: {e}"
                )

            if not pose:
                raise ValueError(
                    f"{pending_trip.trip.route[0]} pose is None,  cannot assemble_cost_matrix"
                )

            if pending_trip.trip.priority <= 0:
                raise ValueError("trip priority cannot be less than or equal to zero")

            updated_priority = pending_trip.trip.priority * waiting_time_priorities[count]

            if updated_priority <= 0:
                raise ValueError(
                    "updated priority of a trip cannot be less than or equal to zero"
                )

            self.pickup_q.update(
                {
                    pending_trip.trip_id: {
                        "pose": pose,
                        "priority": updated_priority,
                        "route": pending_trip.trip.augmented_route,
                        "sherpa_name": sherpa_name,
                        "booked_by": pending_trip.trip.booked_by,
                    },
                }
            )
            self.ptrip_first_station.append(pending_trip.trip.augmented_route[0])
            count += 1

    def assemble_cost_matrix(self, fleet_name):
        w1 = self.config["eta_power_factor"]
        w2 = self.config["priority_power_factor"]
        max_trips_to_consider = self.config["max_trips_to_consider"]
        # redis_conn = redis.from_url(os.getenv("FM_REDIS_URI"))
        with redis.from_url(os.getenv("FM_REDIS_URI")) as redis_conn:
            cost_matrix = np.ones((len(self.pickup_q), len(self.sherpa_q))) * np.inf
            priority_normalised_cost_matrix = (
                np.ones((len(self.pickup_q), len(self.sherpa_q))) * np.inf
            )
            priority_matrix = np.zeros((len(self.pickup_q), len(self.sherpa_q)))
            i = 0
            for pickup_q, pickup_q_val in self.pickup_q.items():
                j = 0
                for sherpa_q, sherpa_q_val in self.sherpa_q.items():
                    pose_1 = sherpa_q_val["pose"]
                    pose_2 = pickup_q_val["pose"]
                    pickup_priority = pickup_q_val["priority"]
                    route = pickup_q_val["route"]
                    sherpa_name = pickup_q_val["sherpa_name"]
                    temp_stations = [
                        station
                        for station in pickup_q_val["route"]
                        if station in sherpa_q_val["exclude_stations"]
                    ]

                    if len(temp_stations) > 0:
                        self.logger.info(
                            f"cannot use {sherpa_q} for trip_id: {pickup_q}, reason: sherpa restricted from going to {temp_stations}"
                        )
                        total_eta = np.inf
                    elif sherpa_q_val["fleet_status"] == FleetStatus.MAINTENANCE:
                        self.logger.info(
                            f"cannot send {sherpa_q} to {route}, fleet in maintenance mode"
                        )
                        total_eta = np.inf
                    elif (
                        sherpa_q_val["fleet_status"] == FleetStatus.STOPPED
                        and pickup_q_val["booked_by"].find(f"park_{sherpa_q}") == -1
                    ):
                        self.logger.info(f"cannot send {sherpa_q} to {route}, fleet stopped")
                        total_eta = np.inf
                    elif (
                        sherpa_q_val["parking_mode"] is True
                        and pickup_q_val["booked_by"].find(f"park_{sherpa_q}") == -1
                    ):
                        self.logger.info(
                            f"cannot send {sherpa_q} to {route}, sherpa in parking mode"
                        )
                        total_eta = np.inf
                    elif i + 1 > max_trips_to_consider:
                        self.logger.info(
                            f"cannot send {sherpa_q} to {route}, num trips greater than max_trips_to_consider, num_trips: {i+1}"
                        )
                        total_eta = np.inf
                    elif sherpa_name and sherpa_name != sherpa_q:
                        self.logger.info(
                            f"cannot assign {sherpa_q} for trip_id: {pickup_q}, can be assigned only to {sherpa_name} "
                        )
                        total_eta = np.inf
                    else:
                        route_length = utils_util.get_route_length(
                            pose_1, pose_2, fleet_name, redis_conn
                        )
                        total_eta = route_length + sherpa_q_val["remaining_eta"]

                    # to handle w1 == 0  and eta == np.inf case
                    weighted_total_eta = (
                        (total_eta**w1) if (total_eta != np.inf) else total_eta
                    )
                    weighted_pickup_priority = (
                        (pickup_priority**w2)
                        if (pickup_priority != np.inf)
                        else pickup_priority
                    )

                    cost_matrix[i, j] = total_eta
                    priority_matrix[i, j] = pickup_priority

                    priority_normalised_cost_matrix[i, j] = (
                        weighted_total_eta / weighted_pickup_priority
                    )

                    j += 1
                i += 1

        """
        Reasons for adding epsilon:
            1. making sure that the values in priority_normalised_cost_matrix are not below 10-3 incase waiting times are higher
            2. It also helps in differentiating multiple entries with eta==0
        """

        epsilon = np.max(priority_matrix, initial=1)

        if len(priority_normalised_cost_matrix) > 0:
            priority_normalised_cost_matrix += epsilon**w2

        return cost_matrix, priority_matrix, priority_normalised_cost_matrix

    def update_pending_trips(self, dbsession, assignments):

        for pickup, sherpa_name in assignments.items():
            ptrip: PendingTrip = dbsession.get_pending_trip_with_trip_id(pickup)
            ptrip.sherpa_name = sherpa_name
            ptrip.trip.status = TripStatus.ASSIGNED
            ptrip.trip.sherpa_name = sherpa_name

        # commit all the changes

    def print_cost_matrix(self, cost_matrix, index, columns, text):
        cost_matrix_df = pd.DataFrame(cost_matrix, index=index, columns=columns)
        self.logger.info(f"{text}:\n{cost_matrix_df.to_markdown()}\n")

    def run(self, dbsession, fleet_names):
        # self.fleet_names = dbsession.get_all_fleet_names()

        self.fleet_names = fleet_names
        self.logger = logging.getLogger("optimal_dispatch")
        self.logger.info(f"will run optimal dispatch logic for {fleet_names}")
        self.fleets = []

        for fleet_name in self.fleet_names:
            self.fleets.append(dbsession.get_fleet(fleet_name))

        self.get_last_assignment_time(dbsession)
        _ = self.are_power_factors_valid()

        for fleet in self.fleets:
            if (
                self.any_new_trips_booked(dbsession, fleet.name)
                or self.any_change_in_sherpa_availability(dbsession, fleet.name)
                or self.any_trips_cancelled(dbsession, fleet.name)
            ):
                if self.all_data_available(dbsession, fleet.name):
                    self.logger.info(f"need to create/update assignments for {fleet.name}")
                    self.update_sherpa_q(dbsession, fleet.name)
                    self.logger.info(f"updated sherpa_q {self.sherpa_q}")

                    self.update_pickup_q(dbsession, fleet.name)
                    self.logger.info(f"updated pickup_q {self.pickup_q}")

                    pickup_list = list(self.pickup_q.keys())
                    sherpa_list = list(self.sherpa_q.keys())

                    (
                        cost_matrix,
                        priority_matrix,
                        priority_normalised_cost_matrix,
                    ) = self.assemble_cost_matrix(fleet.name)

                    text = f"ETA COST MATRIX for {fleet.name}"
                    self.print_cost_matrix(
                        cost_matrix, self.ptrip_first_station, sherpa_list, text
                    )

                    text = f"PRIORITY  MATRIX for {fleet.name}"
                    self.print_cost_matrix(
                        priority_matrix, self.ptrip_first_station, sherpa_list, text
                    )

                    w1 = self.config["eta_power_factor"]
                    w2 = self.config["priority_power_factor"]
                    text = f"ETA COST MATRIX normalised with priority {fleet.name}, w1= {w1}, w2={w2}"
                    self.print_cost_matrix(
                        priority_normalised_cost_matrix,
                        self.ptrip_first_station,
                        sherpa_list,
                        text,
                    )

                    assignments, raw_assignments = self.assign(
                        priority_normalised_cost_matrix, pickup_list, sherpa_list
                    )

                    self.logger.info(f"Raw assignments: {raw_assignments}\n")
                    self.logger.info(f"Assignments- {fleet.name}:\n")
                    for i in range(0, len(assignments)):
                        self.logger.info(
                            f"{list(assignments.values())[i]} ---> {self.ptrip_first_station[i]}, trip_id: {list(assignments.keys())[i]}"
                        )
                    self.logger.info("\n")

                    self.update_pending_trips(dbsession, assignments)
                    self.update_last_assignment_time(dbsession, fleet.name)
                else:
                    self.logger.info(
                        f"data not sufficient to create/update assignments for {fleet.name}"
                    )
            else:
                self.logger.info(f"need not update assignment for {fleet.name}")
