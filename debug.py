import sys
from fleet_simulator import FleetSimulator


if __name__ == "__main__":
    fs = FleetSimulator()

    if sys.argv[1] == "send_sherpa_status":
        getattr(fs, sys.argv[1])(sys.argv[2])
