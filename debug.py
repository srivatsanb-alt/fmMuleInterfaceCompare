import sys
from fleet_simulator import FleetSimulator, MuleAPP
from core.config import Config
import time


if __name__ == "__main__":
    simulator_config = Config.get_simulator_config()

    fs = FleetSimulator()
    if sys.argv[1] == "send_sherpa_status":
        getattr(fs, sys.argv[1])(sys.argv[2])

    if sys.argv[1] == "host_all_mule_app" and simulator_config["simulate"]:
        mule_app = MuleAPP()
        getattr(mule_app, sys.argv[1])()
        while True:
            pass

    if sys.argv[1] == "simulate" and simulator_config["simulate"]:
        fs.initialize_sherpas()
        time.sleep(1)
        fs.act_on_sherpa_events()
