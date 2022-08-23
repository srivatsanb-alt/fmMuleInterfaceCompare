from utils.comms import send_status_update
import logging
from models.db_session import session
import time
import copy


def send_periodic_updates():
    logging.get_logger().info("starting periodic updates script")
    time.sleep(5)
    while True:
        all_fleet_status = session.get_all_fleet()

        for fleet_status in all_fleet_status:
            msg = {}
            all_station_status = session.get_all_station_status()
            all_sherpa_status = session.get_all_sherpa_status()

            sherpa_status_update = {}
            station_status_update = {}

            for sherpa_status in all_sherpa_status:
                if sherpa_status.sherpa.fleet.name == fleet_status.name:
                    sherpa_status_update.update({
                                                sherpa_status.sherpa_name:
                                                sherpa_status.__dict__})

                    sherpa_status_update[sherpa_status.sherpa_name].update(
                                                sherpa_status.sherpa.__dict__)

            for station_status in all_station_status:
                if station_status.station.fleet.name == fleet_status.name:
                    station_status_update.update({station_status.station_name:
                                                  station_status.__dict__})

                    sherpa_status_update[station_status.station_name].update(
                                            station_status.station.__dict__)

            msg.update({"sherpa_status": sherpa_status_update})
            msg.update({"station_status": station_status_update})
            msg.update({"fleet_status": fleet_status.__dict__})
            msg.update({"fleet_name": fleet_status.name})
            msg.update({"type": "fleet_status"})
            send_status_update(copy.deepcopy(msg))

        time.sleep(1)
