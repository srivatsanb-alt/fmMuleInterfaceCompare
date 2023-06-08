import time
import redis
import json
import os
import logging
from typing import List
from fastapi import Depends, APIRouter, File, UploadFile

# ati code imports
from models.db_session import DBSession
import models.fleet_models as fm
import models.misc_models as mm
import models.request_models as rqm
from utils.rq_utils import Queues
import app.routers.dependencies as dpd
import core.constants as cc

# manages all the http requests for Sherpa
router = APIRouter(
    prefix="/api/v1/sherpa",
    tags=["sherpa"],
    # dependencies=[Depends(get_sherpa)],
    responses={404: {"description": "Not found"}},
)


# checks connection of sherpa with fleet manager
@router.get("/check_connection")
async def check_connection():
    return {"uvicorn": "I am alive"}


@router.get("/basic_info")
async def basic_info(sherpa_name: str = Depends(dpd.get_sherpa)):
    response = {}

    if not sherpa_name:
        dpd.raise_error("Unknown requester", 401)

    with DBSession() as dbsession:
        sherpa: fm.Sherpa = dbsession.get_sherpa(sherpa_name)
        response = {
            "fleet_name": sherpa.fleet.name,
            "TZ": os.getenv("PGTZ"),
            "customer": sherpa.fleet.customer,
            "site": sherpa.fleet.site,
            "location": sherpa.fleet.location,
        }

    return response


# checks connection of sherpa with fleet manager
@router.get("/is_sherpa_version_compatible/{version}")
async def is_sherpa_version_compatible(
    version: str, sherpa_name: str = Depends(dpd.get_sherpa)
):
    allowed = True
    if not sherpa_name:
        dpd.raise_error("Unknown requester", 401)

    with DBSession() as dbsession:
        sherpa: fm.Sherpa = dbsession.get_sherpa(sherpa_name)
        software_compatability = dbsession.get_compatability_info()
        sherpa_versions = software_compatability.info.get("sherpa_versions", [])
        if version not in sherpa_versions:
            allowed = False

            # change only if sherpa is already not disabled
            if sherpa.status.disabled_reason != cc.DisabledReason.EMERGENCY_STOP:
                sherpa.status.disabled = True
                sherpa.status.disabled_reason = cc.DisabledReason.SOFTWARE_NOT_COMPATIBLE

        elif sherpa.status.disabled_reason == cc.DisabledReason.SOFTWARE_NOT_COMPATIBLE:
            sherpa.status.disabled = False
            sherpa.status.disabled_reason = None

    if not allowed:
        dpd.raise_error(f"Cannot allow sherpa to connect to FM with version {version}")

    return {}


# initiates sherpa
@router.post("/init")
async def init_sherpa(init_msg: rqm.InitMsg, sherpa: str = Depends(dpd.get_sherpa)):
    dpd.process_req(None, init_msg, sherpa)


# checks if sherpa has reached to its destination and completed its trip
@router.post("/trip/reached")
async def reached(reached_msg: rqm.ReachedReq, sherpa: str = Depends(dpd.get_sherpa)):
    dpd.process_req(None, reached_msg, sherpa)


@router.post("/peripherals")
async def peripherals(
    peripherals_req: rqm.SherpaPeripheralsReq, sherpa: str = Depends(dpd.get_sherpa)
):
    dpd.process_req(None, peripherals_req, sherpa)


@router.post("/access/resource", response_model=rqm.ResourceResp)
async def resource_access(
    resource_req: rqm.ResourceReq, sherpa: str = Depends(dpd.get_sherpa)
):
    queue = Queues.queues_dict["resource_handler"]
    response = await dpd.process_req_with_response(queue, resource_req, sherpa)
    return rqm.ResourceResp.from_json(response)


@router.get("/verify_fleet_files", response_model=rqm.VerifyFleetFilesResp)
async def verify_fleet_files(sherpa: str = Depends(dpd.get_sherpa)):
    response = await dpd.process_req_with_response(
        None, rqm.SherpaReq(type="verify_fleet_files", timestamp=time.time()), sherpa
    )
    return rqm.VerifyFleetFilesResp.from_json(response)


@router.post("/fatal_error")
async def fatal_errors(err_info: rqm.ErrInfo, sherpa: str = Depends(dpd.get_sherpa)):
    if not sherpa:
        dpd.raise_error("Unknown requester", 401)

    with DBSession() as dbsession:
        fm_incident = mm.FMIncidents(
            type=mm.FMIncidentTypes.mule_error,
            code=err_info.err_code,
            unique_id=err_info.unique_id,
            entity_name=sherpa,
            module=err_info.module,
            sub_module=err_info.sub_module,
            message=err_info.err_msg,
            display_message=err_info.err_disp_msg,
            recovery_message=err_info.recovery_msg,
            data_upload_status="in_progress",
            other_info=err_info.other_info,
        )
        dbsession.add_to_session(fm_incident)

    return {}


@router.post("/req_ack/{req_id}")
async def ws_ack(req: rqm.WSResp, req_id: str):
    redis_conn = redis.from_url(os.getenv("FM_REDIS_URI"))
    if req.success:
        if req.response is None:
            req.response = {}
        redis_conn.set(f"response_{req_id}", json.dumps(req.response))

    redis_conn.setex(
        f"success_{req_id}",
        int(redis_conn.get("default_job_timeout_ms").decode()),
        json.dumps(req.success),
    )

    return {}


@router.get("/get_static_files_auth_credentials")
async def get_static_files_auth_credentials(sherpa: str = Depends(dpd.get_sherpa)):
    if not sherpa:
        dpd.raise_error("Unknown requester", 401)

    response = {
        "user_name": os.getenv("ATI_STATIC_AUTH_USERNAME"),
        "password": os.getenv("ATI_STATIC_AUTH_PASSWORD"),
    }
    return response


# alerts the FM with messages from Sherpa
@router.post("/alerts")
async def sherpa_alerts(
    alert_msg: rqm.SherpaAlertMsg, sherpa: str = Depends(dpd.get_sherpa)
):
    with DBSession() as dbsession:
        sherpa_obj = dbsession.get_sherpa(sherpa)
        alert = f"Got an alert from {sherpa}, "

        if alert_msg.trolley_load_cell:
            alert = alert + alert_msg.trolley_load_cell
        elif alert_msg.low_battery_alarm:
            alert = alert + alert_msg.low_battery_alarm
        elif alert_msg.obstructed:
            alert = alert + alert_msg.obstructed
        elif alert_msg.emergency_button:
            alert = alert + alert_msg.emergency_button
        elif alert_msg.user_pause:
            alert = alert + alert_msg.user_pause
        else:
            dpd.raise_error("Invalid alert msg")

        dbsession.add_notification(
            [sherpa_obj.name, sherpa_obj.fleet.name],
            alert,
            mm.NotificationLevels.action_request,
            mm.NotificationModules.generic,
        )


@router.post("/upload_files/{type}")
async def upload_files(
    type: str,
    uploaded_files: List[UploadFile] = File(...),
    sherpa_name: str = Depends(dpd.get_sherpa),
):

    response = []
    if not sherpa_name:
        dpd.raise_error("Unknown requester", 401)

    augment_filename = False
    # error data filenames will be unique
    # all config files will be consolidated.toml needs to be augmented with sherpa_name
    if type in ["configs"]:
        augment_filename = True

    with DBSession() as dbsession:
        sherpa = dbsession.get_sherpa(sherpa_name)
        fleet_name = sherpa.fleet.name

        dir_to_save = os.path.join(
            os.getenv("FM_STATIC_DIR"), "sherpa_uploads", fleet_name, type
        )

        if not os.path.exists(dir_to_save):
            os.makedirs(dir_to_save)

        for file in uploaded_files:
            new_file_name = file.filename

            if augment_filename:
                file_name, ext = file.filename.rsplit(".", 1)
                new_file_name = file_name + f"_{sherpa_name}" + f".{ext}"

            file_path = os.path.join(dir_to_save, new_file_name)
            try:
                with open(file_path, "wb") as f:
                    f.write(await file.read())
                logging.getLogger("uvicorn").info(f"Uploaded file:{file_path} successfully")

            except Exception as e:
                dpd.raise_error(f"Couldn't upload file: {file_path}, exception: {e}")

            finally:
                file.file.close()

            response.append(file_path)

    return response
