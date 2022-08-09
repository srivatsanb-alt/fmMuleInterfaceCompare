from typing import List
from core.db import session_maker
from sqlalchemy.orm import Session

from models.fleet_models import Fleet, MapFile, Sherpa, SherpaStatus, Station, StationStatus
from models.trip_models import OngoingTrip, PendingTrip, Trip, TripLeg


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

    def get_map_files(self, fleet_name: str) -> List[MapFile]:
        fleet: Fleet = self.session.query(Fleet).filter(Fleet.name == fleet_name).one()
        return self.session.query(MapFile).filter(MapFile.map_id == fleet.map_id).all()

    def get_sherpa(self, name: str) -> Sherpa:
        return self.session.query(Sherpa).filter(Sherpa.name == name).one()

    def get_all_sherpas(self) -> List[SherpaStatus]:
        return self.session.query(SherpaStatus).all()

    def get_sherpa_status(self, name: str) -> SherpaStatus:
        return (
            self.session.query(SherpaStatus).filter(SherpaStatus.sherpa_name == name).one()
        )

    def get_station(self, name: str) -> Station:
        return self.session.query(Station).filter(Station.name == name).one()

    def get_station_status(self, name: str) -> StationStatus:
        return (
            self.session.query(StationStatus)
            .filter(StationStatus.station_name == name)
            .one()
        )

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
            return self.session.query(TripLeg).filter(
                TripLeg.id == ongoing_trip.trip_leg_id
            )

    def delete_pending_trip(self, pending_trip):
        self.session.delete(pending_trip)

    def delete_ongoing_trip(self, ongoing_trip):
        self.session.delete(ongoing_trip)


session = DBSession()
