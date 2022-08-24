from utils.comms import send_status_update
import logging
from models.db_session import session
import time


def get_fleet_status_msg(fleet):
    msg = {}
    all_station_status = session.get_all_station_status()
    all_sherpa_status = session.get_all_sherpa_status()

    sherpa_status_update = {}
    station_status_update = {}

    if all_sherpa_status:
        for sherpa_status in all_sherpa_status:
            if sherpa_status.sherpa.fleet.name == fleet.name:
                sherpa_status_update.update({
                                            sherpa_status.sherpa_name:
                                            sherpa_status.__dict__})

                sherpa_status_update[sherpa_status.sherpa_name].update(
                                            sherpa_status.sherpa.__dict__)

    if all_station_status:
        for station_status in all_station_status:
            if station_status.station.fleet.name == fleet.name:
                station_status_update.update({station_status.station_name:
                                              station_status.__dict__})

                sherpa_status_update[station_status.station_name].update(
                                        station_status.station.__dict__)

    msg.update({"sherpa_status": sherpa_status_update})
    msg.update({"station_status": station_status_update})
    msg.update({"fleet_status": fleet.__dict__})
    msg.update({"fleet_name": fleet.name})
    msg.update({"type": "fleet_status"})

    return msg


def send_periodic_updates():
    logging.get_logger().info("starting periodic updates script")
    time.sleep(5)
    while True:
        all_fleets = session.get_all_fleets()
        for fleet in all_fleets:
            msg = get_fleet_status_msg(fleet)
            send_status_update(msg)

        time.sleep(0.5)
