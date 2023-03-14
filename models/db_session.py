from typing import List
from core.db import session_maker
from sqlalchemy import func
from sqlalchemy.orm import Session
from models.frontend_models import FrontendUser
from models.misc_models import Notifications
from models.fleet_models import (
    Fleet,
    MapFile,
    Sherpa,
    SherpaStatus,
    Station,
    StationStatus,
    SherpaEvent,
    AvailableSherpas,
)
from models.trip_models import OngoingTrip, PendingTrip, Trip, TripLeg, TripAnalytics
from models.visa_models import ExclusionZone, VisaAssignment
from utils.util import check_if_timestamp_has_passed
import datetime
from plugins.conveyor.conveyor_models import ConvInfo, ConvTrips


class DBSession:
    def __init__(self):
        self.session: Session = session_maker()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type or exc_value or traceback:
            self.close(commit=False)
        else:
            self.close()

    def close(self, commit=True):
        if commit:
            self.session.commit()
        self.session.close()

    def close_on_error(self):
        self.session.close()

    def add_to_session(self, obj):
        self.session.add(obj)
        self.session.flush()
        self.session.refresh(obj)

    def create_trip(self, route, priority, metadata=None, booking_id=None, fleet_name=None):
        trip = Trip(
            route=route,
            priority=priority,
            metadata=metadata,
            fleet_name=fleet_name,
            booking_id=booking_id,
        )
        self.add_to_session(trip)
        return trip

    def create_pending_trip(self, trip_id):
        pending_trip = PendingTrip(trip_id=trip_id)
        self.add_to_session(pending_trip)
        return pending_trip

    def create_ongoing_trip(self, sherpa, trip_id):
        ongoing_trip = OngoingTrip(sherpa_name=sherpa, trip_id=trip_id)
        self.add_to_session(ongoing_trip)
        ongoing_trip.init()
        return ongoing_trip

    def create_trip_leg(self, trip_id, curr_station: str, next_station: str):
        trip_leg = TripLeg(trip_id, curr_station, next_station)
        self.add_to_session(trip_leg)
        return trip_leg

    def get_new_booking_id(self):
        booking_id = self.session.query(func.max(Trip.id)).first()
        if booking_id[0]:
            return booking_id[0] + 1
        return 1

    def get_fleet(self, fleet_name: str) -> Fleet:
        return self.session.query(Fleet).filter(Fleet.name == fleet_name).one_or_none()

    def create_exclusion_zone(self, zone_name, zone_type):
        zone_id = f"{zone_name}_{zone_type}"
        ezone = ExclusionZone(zone_id=zone_id)
        self.add_to_session(ezone)
        return ezone

    def add_linked_zone(self, zone_name, zone_type, linked_zone_name, linked_zone_type):
        ezone = self.get_exclusion_zone(zone_name, zone_type)
        linked_ezone = self.get_exclusion_zone(linked_zone_name, linked_zone_type)
        ezone.prev_linked_gates.append(linked_ezone)
        linked_ezone.next_linked_gates.append(ezone)

    def get_all_visas_held(self):
        return self.session.query(VisaAssignment).all()

    def get_visa_held(self, sherpa_name: str):
        return (
            self.session.query(VisaAssignment)
            .filter(VisaAssignment.sherpa_name == sherpa_name)
            .all()
        )

    def get_all_visa_assignments(self):
        return self.session.query(VisaAssignment).all()

    def get_all_fleets(self) -> List[Fleet]:
        return self.session.query(Fleet).all()

    def get_all_fleet_names(self) -> List[str]:
        all_fleets = self.session.query(Fleet).all()
        fleet_names = []
        for fleet in all_fleets:
            fleet_names.append(fleet.name)
        return fleet_names

    def get_map_files(self, fleet_name: str) -> List[MapFile]:
        fleet: Fleet = self.session.query(Fleet).filter(Fleet.name == fleet_name).one()
        return self.session.query(MapFile).filter(MapFile.map_id == fleet.map_id).all()

    def get_sherpa(self, name: str) -> Sherpa:
        return self.session.query(Sherpa).filter(Sherpa.name == name).one_or_none()

    def get_all_sherpa_names(self) -> List[str]:
        all_sherpas = self.session.query(Sherpa).all()
        sherpa_names = []
        for sherpa in all_sherpas:
            sherpa_names.append(sherpa.name)
        return sherpa_names

    def get_all_sherpas(self) -> List[Sherpa]:
        return self.session.query(Sherpa).all()

    def get_all_conveyors(self) -> List[ConvInfo]:
        return self.session.query(ConvInfo).all()

    def get_all_conveyor_trips(self) -> List[ConvInfo]:
        return self.session.query(ConvTrips).all()

    def get_conveyor(self, name: str) -> ConvInfo:
        return self.session.query(ConvInfo).filter(ConvInfo.name == name).one_or_none()

    def get_all_sherpas_in_fleet(self, fleet_name: str) -> List[Sherpa]:
        return (
            self.session.query(Sherpa)
            .join(Sherpa.fleet)
            .filter(Fleet.name == fleet_name)
            .all()
        )

    def get_sherpa_by_api_key(self, hashed_api_key: str) -> Sherpa:
        return (
            self.session.query(Sherpa)
            .filter(Sherpa.hashed_api_key == hashed_api_key)
            .one_or_none()
        )

    def get_sherpa_availability(self, sherpa_name: str):
        return (
            self.session.query(AvailableSherpas)
            .filter(AvailableSherpas.sherpa_name == sherpa_name)
            .one_or_none()
        )

    def get_all_available_sherpa_names(self, fleet_name: str):
        available_sherpa_names = []

        temp = (
            self.session.query(AvailableSherpas.sherpa_name)
            .filter(AvailableSherpas.fleet_name == fleet_name)
            .filter(AvailableSherpas.available.is_(True))
            .all()
        )
        for val in temp:
            available_sherpa_names.append(val[0])

        return available_sherpa_names

    def get_frontend_user(self, name: str, hashed_password: str) -> FrontendUser:
        return (
            self.session.query(FrontendUser)
            .filter(
                FrontendUser.name == name, FrontendUser.hashed_password == hashed_password
            )
            .one_or_none()
        )

    def get_all_sherpa_status(self) -> List[SherpaStatus]:
        return self.session.query(SherpaStatus).all()

    def get_all_stale_sherpa_status(self, heartbeat_interval):
        filter_time = datetime.datetime.now() + datetime.timedelta(
            seconds=-heartbeat_interval
        )
        return (
            self.session.query(SherpaStatus)
            .filter(SherpaStatus.updated_at < filter_time)
            .all()
        )

    def get_sherpa_status(self, name: str) -> SherpaStatus:
        return (
            self.session.query(SherpaStatus).filter(SherpaStatus.sherpa_name == name).one()
        )

    def get_sherpa_events(self, sherpa_name: str, num_events=10) -> List[SherpaEvent]:
        return (
            self.session.query(SherpaEvent)
            .filter(SherpaEvent.sherpa_name == sherpa_name)
            .order_by(SherpaEvent.created_at.desc())
            .limit(num_events)
            .all()
        )

    def get_station(self, name: str) -> Station:
        return self.session.query(Station).filter(Station.name == name).one()

    def get_all_stations(self) -> List[Station]:
        return self.session.query(Station).all()

    def get_all_stations_in_fleet(self, fleet_name: str) -> List[Station]:
        return (
            self.session.query(Station)
            .join(Station.fleet)
            .filter(Fleet.name == fleet_name)
            .all()
        )

    def get_station_status(self, name: str) -> StationStatus:
        return (
            self.session.query(StationStatus)
            .filter(StationStatus.station_name == name)
            .one()
        )

    def get_all_station_status(self) -> List[StationStatus]:
        return self.session.query(StationStatus).all()

    def get_fleet_name_from_route(self, route: List):
        prev_fleet_name = None
        fleet_name = None
        for station_name in route:
            station = self.session.query(Station).filter(Station.name == station_name).one()
            fleet_name = station.fleet.name
            if prev_fleet_name and prev_fleet_name != fleet_name:
                raise Exception(
                    "invalid route, all stations should belong to the same fleet"
                )
            prev_fleet_name = fleet_name

        return fleet_name

    def get_trip(self, trip_id):
        return self.session.query(Trip).filter(Trip.id == trip_id).one()

    def get_trips_with_booking_id(self, booking_id):
        return self.session.query(Trip).filter(Trip.booking_id == booking_id).all()

    def get_pending_trip(self, sherpa_name: str):
        pending_trips = (
            self.session.query(PendingTrip)
            .filter(PendingTrip.sherpa_name == sherpa_name)
            .all()
        )

        for pending_trip in pending_trips:
            if pending_trip.trip.scheduled:
                if not check_if_timestamp_has_passed(pending_trip.trip.start_time):
                    continue
            return pending_trip
        return None

    def get_pending_trips_with_fleet_name(self, fleet_name: str):
        return (
            self.session.query(PendingTrip)
            .join(PendingTrip.trip)
            .filter(Trip.fleet_name == fleet_name)
            .all()
        )

    def get_sherpas_with_pending_trip(self):
        sherpas = []
        temp = self.session.query(PendingTrip.sherpa_name).all()
        for val in temp:
            sherpas.append(val[0])
        return sherpas

    def get_ongoing_trip(self, sherpa_name: str):
        return (
            self.session.query(OngoingTrip)
            .filter(OngoingTrip.sherpa_name == sherpa_name)
            .one_or_none()
        )

    def get_enroute_trip(self, sherpa_name: str):
        return (
            self.session.query(Trip)
            .filter(Trip.sherpa_name == sherpa_name)
            .filter(Trip.status == "en_route")
            .one_or_none()
        )

    def get_all_ongoing_trips(self):
        return self.session.query(OngoingTrip).all()

    def get_all_ongoing_trips_fleet(self, fleet_name: str):
        return (
            self.session.query(OngoingTrip)
            .join(OngoingTrip.trip)
            .filter(Trip.fleet_name == fleet_name)
            .all()
        )

    def get_ongoing_trip_with_trip_id(self, trip_id):
        return (
            self.session.query(OngoingTrip)
            .filter(OngoingTrip.trip_id == trip_id)
            .one_or_none()
        )

    def get_pending_trip_with_trip_id(self, trip_id):
        return (
            self.session.query(PendingTrip)
            .filter(PendingTrip.trip_id == trip_id)
            .one_or_none()
        )

    def get_trip_with_booking_id(self, booking_id):
        return self.session.query(Trip).filter(Trip.booking_id == booking_id).all()

    def get_trip_ids_with_timestamp(self, booked_from, booked_till):

        temp = (
            self.session.query(Trip.id)
            .filter(Trip.booking_time > booked_from)
            .filter(Trip.booking_time < booked_till)
            .all()
        )
        trip_ids = []

        for vals in temp:
            trip_ids.append(vals[0])

        return trip_ids

    def get_trip_analytics(self, trip_leg_id):
        return (
            self.session.query(TripAnalytics)
            .filter(TripAnalytics.trip_leg_id == trip_leg_id)
            .one_or_none()
        )

    def get_last_n_trips(self, last_n=10):
        return self.session.query(Trip).order_by(Trip.id.desc()).limit(last_n).all()

    def get_trip_leg(self, sherpa_name: str):
        ongoing_trip: OngoingTrip = self.get_ongoing_trip(sherpa_name)
        if ongoing_trip:
            return (
                self.session.query(TripLeg)
                .filter(TripLeg.id == ongoing_trip.trip_leg_id)
                .one_or_none()
            )

    def get_all_trip_legs(self, trip_id: int):
        temp = self.session.query(TripLeg.id).filter(TripLeg.trip_id == trip_id).all()
        trip_leg_ids = []
        for vals in temp:
            trip_leg_ids.append(vals[0])
        return trip_leg_ids

    def get_exclusion_zone(self, zone_name, zone_type) -> ExclusionZone:
        zone_id = f"{zone_name}_{zone_type}"
        return (
            self.session.query(ExclusionZone)
            .filter(ExclusionZone.zone_id == zone_id)
            .one_or_none()
        )

    def delete_pending_trip(self, pending_trip):
        self.session.delete(pending_trip)

    def delete_ongoing_trip(self, ongoing_trip):
        self.session.delete(ongoing_trip)

    def add_notification(
        self, entity_names, log, log_level, module, repetitive=False, repetition_freq=None
    ):
        new_notification = Notifications(
            entity_names=entity_names,
            log=log,
            log_level=log_level,
            module=module,
            cleared_by=[],
            repetitive=repetitive,
            repetition_freq=repetition_freq,
        )
        self.add_to_session(new_notification)

    def get_notifications(self):
        return self.session.query(Notifications).all()

    def get_notifications_with_id(self, id):
        return (
            self.session.query(Notifications).filter(Notifications.id == id).one_or_none()
        )

    def delete_notification(self, id):
        self.session.query(Notifications).filter(Notifications.id == id).delete()
