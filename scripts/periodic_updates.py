import json
import logging
import time
import os
import redis

# ati code imports
from utils.comms import send_status_update, send_notification
from utils.util import get_table_as_dict, report_error, proc_retry
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

def get_all_zones_msg(dbsession):
    all_zones = dbsession.get_all_exclusion_zones()
    zones_msg = {}
    
    for zone in all_zones:
        zone_id = zone.zone_id
        
        # Split zone_id to get zone_name and zone_type
        if "_" in zone_id:
            parts = zone_id.rsplit("_", 1)
            if len(parts) == 2:
                zone_name = parts[0]
                zone_type = parts[1]
        else:
            zone_name = zone_id
            zone_type = ""
        
        # Get assignments for this specific zone
        assignments = dbsession.get_all_visa_assignments_as_dict(zone_id)
        
        # Create zone info with basic properties
        zone_info = {
            "zone_id": zone_id,
            "zone_name": zone_name,
            "zone_type": zone_type,
            "exclusivity": zone.exclusivity,
            "fleets": zone.fleets,
            "created_at": str(zone.created_at) if zone.created_at else None,
            "updated_at": str(zone.updated_at) if zone.updated_at else None,
            "resident_entities": [],
            "waiting_entities": []
        }
        
        # Add resident entities
        for entity in assignments["resident_entities"]:
            entity_name = entity["entity_name"]
            entity_type = "sherpa" if dbsession.get_sherpa(entity_name) else "superuser"
            zone_info["resident_entities"].append({
                "entity_name": entity_name,
                "entity_type": entity_type,
                "granted_time": entity["granted_time"]
            })
        
        # Add waiting entities
        for entity in assignments["waiting_entities"]:
            entity_name = entity["entity_name"]
            entity_type = "sherpa" if dbsession.get_sherpa(entity_name) else "superuser"
            zone_info["waiting_entities"].append({
                "entity_name": entity_name,
                "entity_type": entity_type,
                "denied_time": entity["denied_time"],
                "reason": entity["reason"]
            })
        
        zones_msg[zone_id] = zone_info
    
    zones_msg["type"] = "visas_held"
    return zones_msg


def get_visas_held_msg(dbsession):
    all_visas_held = dbsession.get_all_visa_assignments()
    visa_msg = {}
    for visa_held in all_visas_held:
        sherpa_visas = visa_msg.get(visa_held.sherpa_name, {})
        zone_ids = sherpa_visas.get("zone_ids", [])
        zone_ids.append(visa_held.zone_id.rsplit("_", 1)[0])
        zone_types = sherpa_visas.get("zone_types", [])
        zone_types.append(visa_held.zone_id.rsplit("_", 1)[1])
        if visa_held.sherpa_name is not None:
            visa_msg.update(
                {visa_held.sherpa_name: {"zone_ids": zone_ids, "zone_types": zone_types, "vehicle_type": "sherpa"}}
            )
        else:
            visa_msg.update(
                {visa_held.user_name: {"zone_ids": zone_ids, "zone_types": zone_types, "vehicle_type": "superuser"}}
            )
    visa_msg["type"] = "visas_held"
    return visa_msg


def get_all_alert_notifications(dbsession):
    all_alerts = dbsession.get_notifications_filter_with_log_level(
        mm.NotificationLevels.alert
    )
    alert_msg_list = []
    alert_msg = {}
    alert_msg["type"] = mm.NotificationLevels.alert
    alert_msg["modules"] = []

    fleet_names = dbsession.get_all_fleet_names()

    for fleet_name in fleet_names:
        fleet_alert_msg = {
            "type": mm.NotificationLevels.alert,
            "modules": [],
            "fleet_name": fleet_name,
        }

        for alert in all_alerts:
            if fleet_name in alert.entity_names:  
                if alert.module not in fleet_alert_msg["modules"]:
                    fleet_alert_msg[alert.module] = {}
                    fleet_alert_msg["modules"].append(alert.module)
                fleet_alert_msg[alert.module].update(
                    {alert.id: get_table_as_dict(mm.Notifications, alert)}
                )
        if fleet_alert_msg["modules"]:
            alert_msg_list.append(fleet_alert_msg)
        for alert in all_alerts:
            if not any(elem in alert.entity_names for elem in fleet_names):
                if alert.module not in alert_msg["modules"]:
                    alert_msg[alert.module] = {}
                    alert_msg["modules"].append(alert.module)
                    alert_msg["fleet_name"] = 'all_hands_map'
                alert_msg[alert.module].update(
                    {alert.id: get_table_as_dict(mm.Notifications, alert)}
                )
    if len(alert_msg_list) == 0 or alert_msg["modules"]:
        alert_msg_list.append(alert_msg)
    return alert_msg_list


def send_fleet_level_notifications(dbsession, fleet_name):
    notification_gen = dbsession.yield_notifications_grouped_by_log_level_and_modules(
        fleet_name,
        skip_log_levels=[
            mm.NotificationLevels.alert,
            mm.NotificationLevels.stale_alert_or_action,
        ],
        skip_modules=[],
    )
    action_requests = {
        "type": mm.NotificationLevels.action_request,
        "fleet_name": fleet_name,
        "modules": [],
    }
    all_infos = {
        "type": mm.NotificationLevels.info,
        "fleet_name": fleet_name,
        "modules": [],
    }

    while True:
        try:
            log_level, module, notifications = next(notification_gen)
        except StopIteration:
            break

        if log_level == mm.NotificationLevels.action_request:
            action_requests[module] = {}
            action_requests["modules"].append(module)
            for notification in notifications:
                action_requests[module].update(
                    {notification.id: get_table_as_dict(mm.Notifications, notification)}
                )
        elif log_level == mm.NotificationLevels.info:
            all_infos[module] = {}
            all_infos["modules"].append(module)
            for notification in notifications:
                all_infos[module].update(
                    {notification.id: get_table_as_dict(mm.Notifications, notification)}
                )

    send_notification(all_infos)
    send_notification(action_requests)

@proc_retry()
@report_error
def send_periodic_updates():
    logging.getLogger().info("starting periodic updates script")
    pub = redis.from_url(os.getenv("FM_REDIS_URI"), decode_responses=True)
    with DBSession() as dbsession:
        while True:
            all_fleets = dbsession.get_all_fleets()
            for fleet in all_fleets:
                fleet_status_msg = get_fleet_status_msg(dbsession, fleet)
                send_status_update(fleet_status_msg)

                ongoing_trip_msg = get_ongoing_trips_status(dbsession, fleet)
                send_status_update(ongoing_trip_msg)

                send_fleet_level_notifications(dbsession, fleet.name)

            visa_msg = get_visas_held_msg(dbsession)
            send_status_update(visa_msg)

            zones_msg = get_all_zones_msg(dbsession)
            pub.publish("channel:entities", json.dumps(zones_msg))

            all_alerts = get_all_alert_notifications(dbsession)
            for alert_msg in all_alerts:
                send_notification(alert_msg)

            dbsession.session.expire_all()
            time.sleep(2)
