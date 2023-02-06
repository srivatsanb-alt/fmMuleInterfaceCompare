from utils.comms import send_status_update, send_notification
from utils.util import get_table_as_dict

import utils.fleet_utils as fu
import utils.trip_utils as tu
import logging
from models.db_session import DBSession
from models.fleet_models import SherpaStatus, Sherpa, Fleet, Station, StationStatus
from models.misc_models import Notifications
import time


def get_fleet_status_msg(session, fleet):
    msg = {}
    all_station_status = session.get_all_station_status()
    all_sherpa_status = session.get_all_sherpa_status()

    sherpa_status_update = {}
    station_status_update = {}

    if all_sherpa_status:
        for sherpa_status in all_sherpa_status:
            if sherpa_status.sherpa.fleet.name == fleet.name:
                sherpa_status_update.update(
                    {
                        sherpa_status.sherpa_name: get_table_as_dict(
                            SherpaStatus, sherpa_status
                        )
                    }
                )

                sherpa_status_update[sherpa_status.sherpa_name].update(
                    get_table_as_dict(Sherpa, sherpa_status.sherpa)
                )

    if all_station_status:
        for station_status in all_station_status:
            if station_status.station.fleet.name == fleet.name:
                station_status_update.update(
                    {
                        station_status.station_name: get_table_as_dict(
                            StationStatus, station_status
                        )
                    }
                )

                station_status_update[station_status.station_name].update(
                    get_table_as_dict(Station, station_status.station)
                )

    msg.update({"sherpa_status": sherpa_status_update})
    msg.update({"station_status": station_status_update})
    msg.update({"fleet_status": get_table_as_dict(Fleet, fleet)})
    msg.update({"fleet_name": fleet.name})
    msg.update({"type": "fleet_status"})
    msg.update({"timestamp": time.time()})

    return msg


def get_ongoing_trips_status(session, fleet):
    msg = {}

    all_ongoing_trips_fleet = session.get_all_ongoing_trips_fleet(fleet.name)
    for ongoing_trip in all_ongoing_trips_fleet:
        msg.update({ongoing_trip.trip_id: tu.get_trip_status(ongoing_trip.trip)})

    msg["type"] = "ongoing_trips_status"
    return msg


def get_visas_held_msg(session):
    all_visas_held = session.get_all_visas_held()
    visa_msg = {}
    for visa_held in all_visas_held:
        sherpa_visas = visa_msg.get(visa_held.sherpa_name, {})
        zone_ids = sherpa_visas.get("zone_ids", [])
        zone_ids.append(visa_held.zone_id.rsplit("_", 1)[0])
        zone_types = sherpa_visas.get("zone_types", [])
        zone_types.append(visa_held.zone_id.rsplit("_", 1)[1])
        visa_msg.update(
            {visa_held.sherpa_name: {"zone_ids": zone_ids, "zone_types": zone_types}}
        )
    visa_msg["type"] = "visas_held"
    return visa_msg


def get_notifications(session):
    all_notifications = session.get_notifications()
    notification_msg = {}
    notification_msg["type"] = "notifications"
    for notification in all_notifications:
        notification_msg.update(
            {notification.id: get_table_as_dict(Notifications, notification)}
        )

    return notification_msg


def send_periodic_updates():
    while True:
        try:
            logging.getLogger().info("starting periodic updates script")
            with DBSession() as session:
                while True:
                    all_fleets = session.get_all_fleets()
                    for fleet in all_fleets:
                        session.session.refresh(fleet)
                        fleet_status_msg = get_fleet_status_msg(session, fleet)
                        send_status_update(fleet_status_msg)

                        ongoing_trip_msg = get_ongoing_trips_status(session, fleet)
                        send_status_update(ongoing_trip_msg)

                    visa_msg = get_visas_held_msg(session)
                    send_status_update(visa_msg)
                    notification_msg = get_notifications(session)

                    send_notification(notification_msg)
                    time.sleep(2)

        except Exception as e:
            logging.getLogger().info(f"exception in periodic updates script {e}")
            time.sleep(2)
