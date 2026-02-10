import sys
import time
import json
import redis
import os
import logging

# ati code imports....
from models.mongo_client import FMMongo
from fleet_simulator import FleetSimulator, MuleWS

import utils.log_utils as lu

# get log config

logger = logging.getLogger("simulator")

if __name__ == "__main__":

    with FMMongo() as fm_mongo:
        simulator_config = fm_mongo.get_document_from_fm_config("simulator")

    if sys.argv[1] == "establish_all_sherpa_ws" and simulator_config["simulate"]:
        mule_ws = MuleWS()
        getattr(mule_ws, sys.argv[1])()

        ## wait indefinitely
        while True:
            time.sleep(1e3)

    if sys.argv[1] == "simulate" and simulator_config["simulate"]:
        fs = FleetSimulator()
        fleet_manager_up = False
        with redis.from_url(os.getenv("FM_REDIS_URI")) as redis_conn:
            while not fleet_manager_up:
                fleet_manager_up = redis_conn.get("is_fleet_manager_up")
                logger.info("waiting for fleet-manager to start")
                if fleet_manager_up is not None:
                    fleet_manager_up = json.loads(fleet_manager_up)
                time.sleep(5)

        fs.initialize_sherpas()
        time.sleep(2)
        fs.book_predefined_trips()
        fs.act_on_sherpa_events()
