import sys
import time
import json
import redis
import toml
import os
from fleet_simulator import FleetSimulator, MuleAPP
from core.config import Config

if __name__ == "__main__":
    simulator_config = Config.get_simulator_config()
    plugins = toml.load(os.path.join(os.getenv("FM_CONFIG_DIR"), "plugin_config.toml"))["all_plugins"]
    simulate_conveyor_plugin = "conveyor" in plugins

    if sys.argv[1] == "host_all_mule_app" and simulator_config["simulate"]:
        mule_app = MuleAPP()
        getattr(mule_app, sys.argv[1])()
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
        if simulate_conveyor_plugin:
            fs.simulate_conveyors()
        fs.act_on_sherpa_events()
