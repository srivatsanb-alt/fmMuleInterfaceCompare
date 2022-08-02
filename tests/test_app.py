from core.db import engine
from models import fleet_models, trip_models
from models.db_session import add_sherpa
from fastapi.testclient import TestClient
from app.main import app


def test_sherpa_init():
    fleet_models.Base.metadata.drop_all(bind=engine)
    trip_models.Base.metadata.drop_all(bind=engine)
    fleet_models.Base.metadata.create_all(bind=engine)
    trip_models.Base.metadata.create_all(bind=engine)

    api_key = add_sherpa("S1", "abcd")

    client = TestClient(app)
    init_msg = {"current_pose": [1.0, 2.0, 3.14]}
    response = client.post("/sherpa/init/", json=init_msg, headers={"x-api-key": api_key})
    print(response.status_code)
    print(response.headers)
    print(response.json())


if __name__ == "__main__":
    test_sherpa_init()
