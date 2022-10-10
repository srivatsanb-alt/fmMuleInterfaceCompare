import sys
from fleet_simulator import FleetSimulator


if __name__ == "__main__":
    fs = FleetSimulator()

    if sys.argv[1] == "send_sherpa_status":
        getattr(fs, sys.argv[1])(sys.argv[2])

    if sys.argv[1] == "host_all_mule_app":
        getattr(fs, sys.argv[1])()
        while True:
            pass

    if sys.argv[1] == "simulate":
        print("Book trips from dashboard to simulate trips")
        fs.initialize_sherpas()
        fs.act_on_sherpa_events()
