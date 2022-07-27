from core.db import session_maker

from models.fleet_models import Sherpa
from models.trip_models import OngoingTrip, TripLeg, Trip
from sqlalchemy.orm import Session


class DBSession:
    def __init__(self):
        self.session: Session = session_maker()
        self.trip = None
        self.ongoing_trip = None
        self.trip_leg = None

    def close(self):
        self.session.commit()
        self.session.close()

    def get_sherpa(self, name: str):
        return self.session.query(Sherpa).filter(Sherpa.name == name).one()

    def new_trip(self, route, priority=0, metadata=None):
        self.trip = Trip(route=route, priority=priority, metadata=metadata)
        self.session.add(self.trip)
        self.session.flush()
        self.session.refresh(self.trip)

    def set_ongoing_trip(self, sherpa: str):
        self.ongoing_trip = (
            self.session.query(OngoingTrip).filter(OngoingTrip.sherpa == sherpa).one()
        )

    def set_trip_leg(self, sherpa: str):
        if self.trip_leg:
            return
        self.set_trip(sherpa)
        trip_leg_id = self.ongoing_trip.trip_leg_id
        self.trip_leg = self.session.query(TripLeg).filter(TripLeg.id == trip_leg_id).one()

    def set_trip(self, sherpa):
        if self.trip:
            return
        if not self.ongoing_trip:
            self.set_ongoing_trip(sherpa)
        trip_id = self.ongoing_trip.trip_id
        self.trip = self.session.query(Trip).filter(Trip.id == trip_id).one()

    def assign_sherpa(self, sherpa: str):
        self.ongoing_trip = OngoingTrip(sherpa=sherpa, trip_id=self.trip.id)
        self.session.add(self.ongoing_trip)
        self.session.flush()
        self.session.refresh(self.ongoing_trip)
        self.trip.assign_sherpa(sherpa)

    def start_trip(self, sherpa: str):
        self.set_trip(sherpa)
        self.trip.start()

    def end_trip(self, sherpa: str, success=True):
        self.set_trip(sherpa)
        self.trip.end(success)
        self.session.delete(self.ongoing_trip)

    def start_leg(self, sherpa: str):
        self.set_trip(sherpa)
        self.trip_leg = TripLeg(
            self.trip.id, self.trip.curr_station(), self.trip.next_station()
        )
        self.session.add(self.trip_leg)
        self.session.flush()
        self.session.refresh(self.trip_leg)
        self.ongoing_trip.set_leg_id(self.trip_leg.id)
        self.trip.start_leg()

    def end_leg(self, sherpa: str):
        self.set_trip_leg(sherpa)
        self.trip_leg.end()
        self.trip.end_leg()


def add_sherpa(sherpa: str, hwid=None, ip_address=None, hashed_api_key=None, fleet_id=None):
    with session_maker() as db:
        sherpa = Sherpa(
            name=sherpa,
            hwid=hwid,
            ip_address=ip_address,
            hashed_api_key=hashed_api_key,
            disabled=False,
            pose=None,
            fleet_id=fleet_id,
        )
        db.add(sherpa)
        db.commit()
