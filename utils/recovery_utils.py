import aioredis

import models.misc_models as mm
import utils.util as utils
import models.request_models as rqm
import app.routers.dependencies as dpd

async def _get_redis_request_id(aredis_conn: aioredis.Redis, entity_name: str) -> str:
    auto_recover_req_id = await aredis_conn.get(f"auto_recover_req_id_{entity_name}")
    return auto_recover_req_id.decode() if auto_recover_req_id is not None else None


async def _delete_redis_request_id(aredis_conn: aioredis.Redis, entity_name: str) -> None:
    await aredis_conn.delete(f"auto_recover_req_id_{entity_name}")


async def _set_redis_request_id(aredis_conn: aioredis.Redis, entity_name: str, req_id: str) -> None:
    await aredis_conn.set(f"auto_recover_req_id_{entity_name}", req_id)


def _get_entity_names_for_notifications(entity_name: str, fleet_name: str, req_id: str) -> list:
    return [entity_name, fleet_name, req_id]


def _delete_existing_notifications(dbsession, entity_names: list) -> None:
    notifications = dbsession.get_notifications_with_entity_names_log_level_and_module(
        entity_names,
        mm.NotificationLevels.event_based,
        mm.NotificationModules.auto_recovery
    )
    for notification in notifications:
        dbsession.delete_notification(notification.id)


def _add_auto_recover_notification(dbsession, entity_names: list, message: str) -> None:
    utils.maybe_add_notification(
        dbsession,
        entity_names,
        message,
        mm.NotificationLevels.event_based,
        mm.NotificationModules.auto_recovery
    )


async def _handle_start_auto_recover(
    aredis_conn: aioredis.Redis, 
    dbsession, 
    entity_name: str, 
    sherpa_status, 
    existing_req_id: str
) -> str:
    if existing_req_id is not None:
        await _delete_redis_request_id(aredis_conn, entity_name)
    
    # TODO: This is a temporary fix to prevent multiple auto recover requests from being sent.
    # We need to remove this once we have a proper auto recover mechanism from frontend.
    is_any_auto_recover_running = dbsession.get_notifications_with_module(mm.NotificationModules.auto_recovery)
    if len(is_any_auto_recover_running) > 0:
        dpd.raise_error("Auto recover is already running")
    
    entity_names = _get_entity_names_for_notifications(
        entity_name,
        sherpa_status.sherpa.fleet.name,
        existing_req_id
    )
    _delete_existing_notifications(dbsession, entity_names)
    
    new_req_id = utils.generate_random_job_id()
    await _set_redis_request_id(aredis_conn, entity_name, new_req_id)
    
    entity_names = _get_entity_names_for_notifications(
        entity_name, 
        sherpa_status.sherpa.fleet.name, 
        new_req_id
    )
    _add_auto_recover_notification(dbsession, entity_names, "Auto recover request started")
    
    return new_req_id


async def _handle_stop_auto_recover(
    aredis_conn: aioredis.Redis, 
    dbsession, 
    entity_name: str, 
    sherpa_status, 
    req_id: str
) -> None:
    
    entity_names = _get_entity_names_for_notifications(
        entity_name, 
        sherpa_status.sherpa.fleet.name, 
        req_id
    )
    _delete_existing_notifications(dbsession, entity_names)
    
    await _delete_redis_request_id(aredis_conn, entity_name)
    
def _create_slam_recover_log_message(slam_recover_req: rqm.SlamRecoverReq, req_id: str) -> str:
    """Create log message for SLAM recovery notification."""
    station_name = slam_recover_req.station_name if slam_recover_req.station_name else None
    position = slam_recover_req.pose if slam_recover_req.pose else None
    error = slam_recover_req.error if slam_recover_req.error else None
    
    if station_name:
        return f"station_name:{station_name}, position:{position}, error:{error}, req_id:{req_id}"
    else:
        return "Station not found"

