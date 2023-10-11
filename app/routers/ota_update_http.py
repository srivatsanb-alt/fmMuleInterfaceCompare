import os
import aioredis
import json
import asyncio
from fastapi import APIRouter, Depends
from requests.auth import HTTPBasicAuth

# ati code imports
import master_fm_comms.mfm_utils as mu

import app.routers.dependencies as dpd


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

    status_code, available_updates_json = mu.send_http_req_to_mfm(
        mfm_context=mfm_context,
        endpoint="get_available_updates",
        req_type="get",
        query="fm",
    )
    if status_code != 200:
        dpd.raise_error("Unable to fetch info on available_updates")

    status_code, auth_json = mu.send_http_req_to_mfm(
        mfm_context=mfm_context,
        endpoint="get_basic_auth",
        req_type="get",
    )
    if status_code != 200:
        dpd.raise_error(
            f"Unable access master_fm: {mfm_context.mfm_ip}:{mfm_context.mfm_port}"
        )
    static_files_auth_username = auth_json["static_files_auth"]["username"]
    static_files_auth_password = auth_json["static_files_auth"]["password"]
    auth = HTTPBasicAuth(static_files_auth_username, static_files_auth_password)

    available_updates = {}
    for available_update_version in available_updates_json["available_updates"]:
        available_updates.update({available_update_version: {}})
        status_code, release_notes = mu.send_http_req_to_mfm(
            mfm_context=mfm_context,
            endpoint="download_file",
            req_type="get",
            query=f"fm/{available_update_version}/release.notes",
            auth=auth,
        )
        if status_code == 200:
            temp = None
            if release_notes is not None:
                temp = release_notes.decode()
            available_updates[available_update_version].update({"release_notes": temp})

        status_code, release_dt = mu.send_http_req_to_mfm(
            mfm_context=mfm_context,
            endpoint="download_file",
            req_type="get",
            query=f"fm/{available_update_version}/release.dt",
            auth=auth,
        )
        if status_code == 200:
            available_updates[available_update_version].update(
                {"release_dt": release_dt.decode()}
            )

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

    status_code, auth_json = mu.send_http_req_to_mfm(
        mfm_context=mfm_context,
        endpoint="get_basic_auth",
        req_type="get",
    )

    if status_code != 200:
        dpd.raise_error(
            f"Unable access master_fm: {mfm_context.mfm_ip}:{mfm_context.mfm_port}"
        )

    registry_username = auth_json["registry_auth"]["username"]
    registry_password = auth_json["registry_auth"]["password"]
    static_files_auth_username = auth_json["static_files_auth"]["username"]
    static_files_auth_password = auth_json["static_files_auth"]["password"]

    command = [
        f"bash /app/scripts/self_updater.sh {mfm_context.server_ip} {mfm_context.server_port} {mfm_context.http_scheme} {fm_version} {registry_username} {registry_password} {static_files_auth_username} {static_files_auth_password} > /app/static/fm_update_progress.log 2>&1"
    ]

    update_proc = await asyncio.create_subprocess_shell(*command)
    await update_proc.wait()

    await redis_conn.delete("update_started")
    await redis_conn.delete("updating_to")

    update_done = await redis_conn.get("update_done")
    update_done = json.loads(update_done)
    if update_done is False:
        await redis_conn.delete("update_done")
        dpd.raise_error(f"Unable to complete the update process")

    # os.system("rm /app/static/fm_update_progress.log")

    return response
