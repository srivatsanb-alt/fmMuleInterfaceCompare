import sys
import time
import json
import redis
import os

# ati code imports....
from models.mongo_client import FMMongo
from fleet_simulator import FleetSimulator, MuleWS

if __name__ == "__main__":

    with FMMongo() as fm_mongo:
        simulator_config = fm_mongo.get_document_from_fm_config("simulator")

    if sys.argv[1] == "establish_all_sherpa_ws" and simulator_config["simulate"]:
        mule_ws = MuleWS()
        getattr(mule_ws, sys.argv[1])()
        while True:
            pass

    if sys.argv[1] == "simulate" and simulator_config["simulate"]:
        fs = FleetSimulator()
        fleet_manager_up = False
        redis_conn = redis.from_url(os.getenv("FM_REDIS_URI"))
        while not fleet_manager_up:
            fleet_manager_up = redis_conn.get("is_fleet_manager_up")
            print("waiting for fleet-manager to start")
            if fleet_manager_up is not None:
                fleet_manager_up = json.loads(fleet_manager_up)
            time.sleep(5)

        fs.initialize_sherpas()
        time.sleep(2)
        fs.book_predefined_trips()
        fs.act_on_sherpa_events()
