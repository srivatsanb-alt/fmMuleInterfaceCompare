import time
from core.db import engine
from models import fleet_models, trip_models
from models.db_session import DBSession
from models.fleet_models import Sherpa
from utils.fleet_utils import add_fleet, add_sherpa, add_sherpa_to_fleet, add_station


def test_sherpa_model():
    fleet_models.Base.metadata.drop_all(bind=engine)
    trip_models.Base.metadata.drop_all(bind=engine)
    fleet_models.Base.metadata.create_all(bind=engine)
    trip_models.Base.metadata.create_all(bind=engine)

    add_sherpa("S1")
    sess = DBSession()
    sherpa: Sherpa = sess.get_sherpa("S1")
    sherpa.initialized = True
    print(sherpa)
    sess.close()


def test_trip_model():
    fleet_models.Base.metadata.drop_all(bind=engine)
    trip_models.Base.metadata.drop_all(bind=engine)
    fleet_models.Base.metadata.create_all(bind=engine)
    trip_models.Base.metadata.create_all(bind=engine)

    add_sherpa("S1")

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


def curl_test():
    fleet_models.Base.metadata.drop_all(bind=engine)
    trip_models.Base.metadata.drop_all(bind=engine)
    fleet_models.Base.metadata.create_all(bind=engine)
    trip_models.Base.metadata.create_all(bind=engine)
    add_fleet("test")
    api_key = add_sherpa("S2", "efgh")
    print(api_key)
    add_sherpa_to_fleet("S2", "test")
    add_station("a", [1.0, 0.0, 3.14])
    add_station("b", [2.0, 0.0, 3.14])
    add_station("c", [3.0, 0.0, 3.14])
    dbs = DBSession()
    trip = dbs.create_trip(["a", "b", "c"])
    dbs.create_pending_trip(trip.id)
    dbs.close()


def init_test():
    dbs = DBSession()
    trip = dbs.create_trip(["a", "b", "c"])
    dbs.create_pending_trip(trip.id)
    dbs.close()


if __name__ == "__main__":
    test_sherpa_model()
    test_trip_model()
