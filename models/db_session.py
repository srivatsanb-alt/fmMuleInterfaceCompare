from typing import List
from core.db import session_maker
from sqlalchemy.orm import Session
from models.frontend_models import FrontendUser
from models.fleet_models import Fleet, MapFile, Sherpa, SherpaStatus, Station, StationStatus
from models.trip_models import OngoingTrip, PendingTrip, Trip, TripLeg
from models.visa_models import ExclusionZone


class DBSession:
    def __init__(self):
        self.session: Session = session_maker()
        # self.trip: Trip = None
        # self.pending_trip: PendingTrip = None
        # self.ongoing_trip: OngoingTrip = None
        # self.trip_leg: TripLeg = None

    def close(self):
        self.session.commit()
        self.session.close()

    def close_on_error(self):
        self.session.close()

    def add_to_session(self, obj):
        self.session.add(obj)
        self.session.flush()
        self.session.refresh(obj)

    def create_trip(self, route, priority=0, metadata=None):
        trip = Trip(route=route, priority=priority, metadata=metadata)
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

    def get_fleet(self, fleet_name: str) -> Fleet:
        return self.session.query(Fleet).filter(Fleet.name == fleet_name).one_or_none()

    def create_exclusion_zone(self, zone_id, zone_type):
        ezone = ExclusionZone(zone_id=zone_id, zone_type=zone_type)
        self.add_to_session(ezone)
        return ezone

    def get_all_fleets(self) -> List[Fleet]:
        return self.session.query(Fleet).all()

    def get_map_files(self, fleet_name: str) -> List[MapFile]:
        fleet: Fleet = self.session.query(Fleet).filter(Fleet.name == fleet_name).one()
        return self.session.query(MapFile).filter(MapFile.map_id == fleet.map_id).all()

    def get_sherpa(self, name: str) -> Sherpa:
        return self.session.query(Sherpa).filter(Sherpa.name == name).one_or_none()

    def get_all_sherpas(self) -> List[Sherpa]:
        return self.session.query(Sherpa).all()

    def get_sherpa_by_api_key(self, hashed_api_key: str) -> Sherpa:
        return (
            self.session.query(Sherpa)
            .filter(Sherpa.hashed_api_key == hashed_api_key)
            .one_or_none()
        )

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

    def get_sherpa_status(self, name: str) -> SherpaStatus:
        return (
            self.session.query(SherpaStatus).filter(SherpaStatus.sherpa_name == name).one()
        )

    def get_station(self, name: str) -> Station:
        return self.session.query(Station).filter(Station.name == name).one()

    def get_all_stations(self) -> List[Station]:
        return self.session.query(Station).all()

    def get_station_status(self, name: str) -> StationStatus:
        return (
            self.session.query(StationStatus)
            .filter(StationStatus.station_name == name)
            .one()
        )

    def get_all_station_status(self) -> List[StationStatus]:
        return self.session.query(StationStatus).all()

    def get_trip(self, trip_id):
        return self.session.query(Trip).filter(Trip.id == trip_id).one()

    def get_pending_trip(self):
        return self.session.query(PendingTrip).first()

    def get_ongoing_trip(self, sherpa: str):
        return (
            self.session.query(OngoingTrip)
            .filter(OngoingTrip.sherpa_name == sherpa)
            .one_or_none()
        )

    def get_trip_leg(self, sherpa: str):
        ongoing_trip: OngoingTrip = self.ongoing_trip(sherpa)
        if ongoing_trip:
            return (
                self.session.query(TripLeg)
                .filter(TripLeg.id == ongoing_trip.trip_leg_id)
                .one_or_none()
            )

    def update_fleet_status(self, fleet_name: str, status: str):
        success = (
            self.session.query(Fleet)
            .filter(Fleet.name == fleet_name)
            .update({Fleet.status: status})
        )

        self.session.commit()
        return self, success

    def enable_disable_sherpa(self, sherpa_name: str, disable: bool):
        success = (
            self.session.query(SherpaStatus)
            .filter(SherpaStatus.sherpa_name == sherpa_name)
            .update({SherpaStatus.disabled: disable})
        )

        self.session.commit()
        return self, success

    def get_exclusion_zone(self, zone_id, zone_type) -> ExclusionZone:
        return (
            self.session.query(ExclusionZone)
            .filter(
                ExclusionZone.zone_id == zone_id and ExclusionZone.zone_type == zone_type
            )
            .one_or_none()
        )

    def delete_pending_trip(self, pending_trip):
        self.session.delete(pending_trip)

    def delete_ongoing_trip(self, ongoing_trip):
        self.session.delete(ongoing_trip)


session = DBSession()
