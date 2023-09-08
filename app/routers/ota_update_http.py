import os
from fastapi import APIRouter, Depends

# ati code imports
import app.routers.dependencies as dpd


router = APIRouter(
    prefix="/api/v1/ota_update",
    tags=["ota_updates"],
    responses={404: {"description": "Not found"}},
)


@router.get("/fm/get_available_updates")
def get_available_updates(
    user_name=Depends(dpd.get_user_from_header),
):
    import master_fm_comms.mfm_utils as mu

    mfm_context = mu.get_mfm_context()

    # status_code, available_updates_json = mu.send_http_req_to_mfm(
    #     mfm_context=mfm_context,
    #     endpoint="get_available_updates",
    #     req_type="get",
    #     query="fm",
    # )
    # if status_code != 200:
    #     dpd.raise_error("Unable to fetch info on available_updates")

    available_updates_json = {"available_updates": ["fm_dev"]}
    available_updates = {}
    for available_update_version in available_updates_json["available_updates"]:
        available_updates.update({available_update_version: {}})
        status_code, release_notes = mu.send_http_req_to_mfm(
            mfm_context=mfm_context,
            endpoint="download_file",
            req_type="get",
            query=f"fm/{available_update_version}/release.notes",
        )
        if status_code == 200:
            temp = None
            if release_notes is not None:
                temp = release_notes.decode()
            available_updates.update(
                {available_update_version.update({"release_notes": temp})}
            )

        status_code, release_dt = mu.send_http_req_to_mfm(
            mfm_context=mfm_context,
            endpoint="download_file",
            req_type="get",
            query=f"fm/{available_update_version}/release.dt",
        )
        if status_code == 200:
            available_updates.update(
                {available_update_version.update({"release_dt": release_dt.decode()})}
            )

    return available_updates


@router.get("/fm/update_to/{fm_version}")
def update_fm(
    fm_version: str,
    user_name=Depends(dpd.get_user_from_header),
):
    response = {}

    import master_fm_comms.mfm_utils as mu

    mfm_context = mu.get_mfm_context()

    status_code, auth_json = mu.send_http_req_to_mfm(
        mfm_context=mfm_context,
        endpoint="get_basic_auth",
        req_type="get",
    )

    # if status_code != 200:
    #    dpd.raise_error(
    #        f"Unable access master_fm: {mfm_context.mfm_ip}:{mfm_context.mfm_port}"
    #    )

    # registry_username = auth_json["registry_auth"]["username"]
    # registry_username = auth_json["registry_auth"]["password"]
    # static_files_auth_username = auth_json["static_files_auth"]["password"]
    # static_files_auth_password = auth_json["static_files_auth"]["password"]

    registry_username = "ati_static_files"
    registry_password = "atiStatic112"
    static_files_auth_username = "a"
    static_files_auth_password = "b"

    os.system("rm /app/static/fm_update_progress.log")

    return_code = os.system(
        f"cd /app && bash scripts/self_updater.sh \
        {mfm_context.server_ip} {mfm_context.server_port} \
        {mfm_context.http_scheme} {fm_version} \
        {registry_username} {registry_password} \
        {static_files_auth_username} \
        {static_files_auth_password} \
        > /app/static/fm_update_progress.log 2>&1 &"
    )

    if return_code != 0:
        dpd.raise_error("Unable to start update process")

    return response
