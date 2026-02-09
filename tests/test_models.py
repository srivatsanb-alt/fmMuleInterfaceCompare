import time
from core.db import engine
from models import fleet_models, trip_models
from models.db_session import DBSession
from utils.fleet_utils import (
    add_update_fleet,
    add_sherpa,
    add_sherpa_to_fleet,
    add_update_station,
)


def test_sherpa_model():
    fleet_models.Base.metadata.drop_all(bind=engine)
    trip_models.Base.metadata.drop_all(bind=engine)
    fleet_models.Base.metadata.create_all(bind=engine)
    trip_models.Base.metadata.create_all(bind=engine)

    add_sherpa("S1", "abcd")
    sess = DBSession()
    sess.close()


def test_trip_model():
    fleet_models.Base.metadata.drop_all(bind=engine)
    trip_models.Base.metadata.drop_all(bind=engine)
    fleet_models.Base.metadata.create_all(bind=engine)
    trip_models.Base.metadata.create_all(bind=engine)

    add_sherpa("S1", "abcd")

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
    from models.fleet_models import StationProperties

    fleet_models.Base.metadata.drop_all(bind=engine)
    trip_models.Base.metadata.drop_all(bind=engine)
    fleet_models.Base.metadata.create_all(bind=engine)
    trip_models.Base.metadata.create_all(bind=engine)
    add_update_fleet(name="test")
    api_key = add_sherpa(
        "S2", hwid="abcd", api_key="MbviPsacmoa-hRB_iXp_HSpTsSTSE-YIbl3bHjCb4uM_abcd"
    )
    print(api_key)
    add_sherpa_to_fleet("S2", "test")
    add_update_station(name="a", pose=[1.0, 0.0, 3.14])
    add_update_station(
        name="b", pose=[2.0, 0.0, 3.14], properties=[StationProperties.AUTO_UNHITCH]
    )
    add_update_station(name="c", pose=[3.0, 0.0, 3.14])


def hall1_test():
    dbs = DBSession()
    trip_models.Trip.__table__.drop(bind=engine)
    trip_models.OngoingTrip.__table__.drop(bind=engine)
    trip_models.PendingTrip.__table__.drop(bind=engine)
    trip = dbs.create_trip(["Start", "S1", "Start"])
    dbs.create_pending_trip(trip.id)
    dbs.close()


def init_test():
    dbs = DBSession()
    trip = dbs.create_trip(["a", "b", "c"])
    dbs.create_pending_trip(trip.id)
    dbs.close()


def ws_conn_test():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    headers = {"x-api-key": "MbviPsacmoa-hRB_iXp_HSpTsSTSE-YIbl3bHjCb4uM_abcd"}
    with client.websocket_connect("/ws/api/v1/sherpa/", headers=headers) as websocket:
        data = {
            "type": "sherpa_status",
            "timestamp": 1654166684,
            "sherpa_name": "S2",
            "current_pose": [1.5, 2.5, 6.28],
            "battery_status": 90,
            "mode": "fleet",
            "error": False,
        }
        websocket.send_json(data)


if __name__ == "__main__":
    test_sherpa_model()
    test_trip_model()
