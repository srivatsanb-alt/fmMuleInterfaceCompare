import time
from core.db import engine
from models import fleet_models, trip_models
from models.db_session import DBSession, add_sherpa
from models.fleet_models import Sherpa


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


if __name__ == "__main__":
    test_sherpa_model()
    test_trip_model()
