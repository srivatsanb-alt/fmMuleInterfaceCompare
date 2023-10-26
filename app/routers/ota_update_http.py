import os
import aioredis
import json
import asyncio
import shutil
import datetime
from fastapi import APIRouter, Depends

# ati code imports
from models.db_session import DBSession
import models.misc_models as mm
import master_fm_comms.mfm_utils as mu
import app.routers.dependencies as dpd
import utils.util as utils_util


router = APIRouter(
    prefix="/api/v1/ota_update",
    tags=["ota_updates"],
    responses={404: {"description": "Not found"}},
)


@router.get("/fm/get_available_updates")
async def get_available_updates(
    user_name=Depends(dpd.get_user_from_header),
):

    mfm_context = mu.get_mfm_context()
    status_code, available_updates_json = mu.get_available_updates_fm(mfm_context)
    if status_code != 200:
        dpd.raise_error("Unable to fetch info on available_updates")

    auth, _ = mu.get_mfm_static_file_auth(mfm_context)
    if auth is None:
        dpd.raise_error(
            f"Unable get auth for master_fm: {mfm_context.mfm_ip}:{mfm_context.mfm_port}"
        )
    available_updates = {}
    for available_update_version in available_updates_json["available_updates"]:
        release_notes, release_dt = mu.get_release_details(
            mfm_context, available_update_version, auth
        )
        available_updates.update({available_update_version: {}})

        available_updates[available_update_version].update({"release_notes": release_notes})
        available_updates[available_update_version].update({"release_dt": release_dt})

    return available_updates


@router.get("/fm/update_to/{fm_version}")
async def update_fm(
    fm_version: str,
    user_name=Depends(dpd.get_user_from_header),
):
    response = {}
    redis_conn = aioredis.Redis.from_url(
        os.getenv("FM_REDIS_URI"), max_connections=10, decode_responses=True
    )

    update_wait_time_ms = int(180e3)
    update_started = await redis_conn.get("update_started")

    if update_started is None:
        await redis_conn.setex("update_started", update_wait_time_ms, json.dumps(True))
        await redis_conn.set("updating_to", fm_version)
        await redis_conn.set("update_done", json.dumps(False))

    else:
        updating_to = await redis_conn.get("updating_to")
        dpd.raise_error(
            f"Already updating to version: {updating_to}, please wait for the update to get completed"
        )

    mfm_context = mu.get_mfm_context()
    _, auth_json = mu.get_mfm_static_file_auth(mfm_context)
    if auth_json is None:
        dpd.raise_error(
            f"Unable get auth for master_fm: {mfm_context.mfm_ip}:{mfm_context.mfm_port}"
        )

    registry_username = auth_json["registry_auth"]["username"]
    registry_password = auth_json["registry_auth"]["password"]
    static_files_auth_username = auth_json["static_files_auth"]["username"]
    static_files_auth_password = auth_json["static_files_auth"]["password"]

    update_progress_log = os.path.join(os.getenv("FM_STATIC_DIR"), "fm_update_progress.log")

    command = [
        f"bash /app/scripts/self_updater.sh {mfm_context.server_ip} {mfm_context.server_port} {mfm_context.http_scheme} {fm_version} {registry_username} {registry_password} {static_files_auth_username} {static_files_auth_password} > {update_progress_log} 2>&1"
    ]

    update_proc = await asyncio.create_subprocess_shell(*command)
    await update_proc.wait()

    await redis_conn.delete("update_started")
    await redis_conn.delete("updating_to")
    update_done = await redis_conn.get("update_done")
    update_done = json.loads(update_done)

    dt_str = utils_util.dt_to_str(datetime.datetime.now())
    dt_str_no_space = dt_str.replace(" ", "-")

    current_data_folder = await redis_conn.get("current_data_folder")
    dest_path = os.path.join(
        os.getenv("FM_STATIC_DIR"), f"fm_update_progress_{dt_str_no_space}.log"
    )
    if current_data_folder:
        fm_backup_path = os.path.join(os.getenv("FM_STATIC_DIR"), "data_backup")
        dest_path = os.path.join(
            fm_backup_path, current_data_folder, f"fm_update_progress_{dt_str_no_space}.log"
        )

    shutil.copy(update_progress_log, dest_path)
    os.system(f"sleep 5 && rm {update_progress_log} &")

    if update_done is False:
        await redis_conn.delete("update_done")
        dpd.raise_error(f"Unable to complete the update process")

    update_log = f"Update to {fm_version} successful! Please switch to {fm_version} with the change FM version button in maintenance page"
    with DBSession() as dbsession:
        dbsession.add_notification(
            dbsession.get_customer_names(),
            update_log,
            mm.NotificationLevels.alert,
            mm.NotificationModules.generic,
        )

    return response
