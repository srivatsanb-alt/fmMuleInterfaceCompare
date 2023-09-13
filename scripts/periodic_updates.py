import logging
import time

# ati code imports
from utils.comms import send_status_update, send_notification
from utils.util import get_table_as_dict
import utils.trip_utils as tu
from models.db_session import DBSession
from models.fleet_models import SherpaStatus, Sherpa, Fleet, Station, StationStatus
import models.misc_models as mm


def get_fleet_status_msg(dbsession, fleet):
    msg = {}
    all_station_status = dbsession.get_all_station_status()
    all_sherpa_status = dbsession.get_all_sherpa_status()

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


def get_ongoing_trips_status(dbsession, fleet):
    msg = {}

    all_ongoing_trips_fleet = dbsession.get_all_ongoing_trips_fleet(fleet.name)
    for ongoing_trip in all_ongoing_trips_fleet:
        msg.update({ongoing_trip.trip_id: tu.get_trip_status(ongoing_trip.trip)})

    msg["type"] = "ongoing_trips_status"
    msg["fleet_name"] = fleet.name

    return msg


def get_visas_held_msg(dbsession):
    all_visas_held = dbsession.get_all_visas_held()
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


def get_all_alert_notifications(dbsession):
    all_alerts = dbsession.get_notifications_filter_with_log_level(
        mm.NotificationLevels.alert
    )
    alert_msg = {}
    alert_msg["type"] = "alerts"
    for alert in all_alerts:
        alert_msg.update({alert.id: get_table_as_dict(mm.Notifications, alert)})

    return alert_msg


def get_fleet_level_notifications(dbsession, fleet_name):
    notification_gen = dbsession.yield_notifications_grouped_by_log_level_and_modules(
        fleet_name, skip_log_levels=[mm.NotificationLevels.alert], skip_modules=[]
    )
    fleet_level_notifications = {}
    fleet_level_notifications["type"] = "non_alert_notifications"
    fleet_level_notifications["fleet_name"] = fleet_name
    while True:
        notifications = []

        try:
            log_level, module, notifications = next(notification_gen)
        except StopIteration:
            break

        fleet_level_notifications[log_level] = {}
        fleet_level_notifications[module] = {}
        for notification in notifications:
            fleet_level_notifications[log_level][module].update(
                {notification.id: get_table_as_dict(mm.Notifications, notification)}
            )

    return fleet_level_notifications


def send_periodic_updates():
    while True:
        try:
            logging.getLogger().info("starting periodic updates script")
            with DBSession() as dbsession:
                while True:
                    all_fleets = dbsession.get_all_fleets()
                    for fleet in all_fleets:
                        fleet_status_msg = get_fleet_status_msg(dbsession, fleet)
                        send_status_update(fleet_status_msg)

                        ongoing_trip_msg = get_ongoing_trips_status(dbsession, fleet)
                        send_status_update(ongoing_trip_msg)

                        fleet_level_notifications = get_fleet_level_notifications(
                            dbsession, fleet.name
                        )
                        send_notification(fleet_level_notifications)

                    visa_msg = get_visas_held_msg(dbsession)
                    send_status_update(visa_msg)

                    all_alerts = get_all_alert_notifications(dbsession)
                    send_notification(all_alerts)

                    # force refresh of all objects
                    dbsession.session.expire_all()
                    time.sleep(2)

        except Exception as e:
            logging.getLogger().info(f"exception in periodic updates script {e}")
            time.sleep(2)
