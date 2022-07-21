import time

from core.db import session_maker, engine

from entities.fleet_entities import add_or_update_sherpa
from models import fleet_models, trip_models
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


def test():
    fleet_models.Base.metadata.drop_all(bind=engine)
    trip_models.Base.metadata.drop_all(bind=engine)
    fleet_models.Base.metadata.create_all(bind=engine)
    trip_models.Base.metadata.create_all(bind=engine)

    add_or_update_sherpa("S1")

    sess = DBSession()
    sess.new_trip(route=["a", "b", "c"])
    time.sleep(2)
    sess.assign_sherpa("S1")
    sess.close()
    time.sleep(2)

    sess = DBSession()
    sess.start_trip("S1")
    sess.close()

    sess = DBSession()
    sess.start_leg("S1")
    sess.close()
    sess = DBSession()
    time.sleep(5)
    sess.end_leg("S1")
    sess.close()

    sess = DBSession()
    time.sleep(2)
    sess.start_leg("S1")
    sess.close()
    sess = DBSession()
    time.sleep(5)
    sess.end_leg("S1")
    sess.close()

    sess = DBSession()
    time.sleep(2)
    sess.start_leg("S1")
    sess.close()
    sess = DBSession()
    time.sleep(5)
    sess.end_leg("S1")
    sess.end_trip("S1")
    sess.close()


if __name__ == "__main__":
    test()
