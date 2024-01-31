from datetime import datetime
import redis
import json
import os
import logging
import pytz
from fastapi import Depends, APIRouter, File, UploadFile
from sqlalchemy.orm.attributes import flag_modified
from fastapi_limiter.depends import RateLimiter

# ati code imports
from models.db_session import DBSession
import models.fleet_models as fm
import models.misc_models as mm
import models.request_models as rqm
from utils.rq_utils import Queues
import utils.util as utils_util
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

    with DBSession(pool=True) as dbsession:
        sherpa: fm.Sherpa = dbsession.get_sherpa(sherpa_name)
        response = {
            "fleet_name": sherpa.fleet.name,
            "TZ": os.getenv("PGTZ"),
            "customer": sherpa.fleet.customer,
            "site": sherpa.fleet.site,
            "location": sherpa.fleet.location,
            "fm_time": (datetime.now(pytz.timezone(os.getenv("PGTZ")))).strftime(
                "%A, %d %b %Y %X %Z"
            ),
        }

    return response


# checks connection of sherpa with fleet manager
@router.get(
    "/is_sherpa_version_compatible/{version}",
    dependencies=[Depends(RateLimiter(times=4, seconds=60))],
)
async def is_sherpa_version_compatible(
    version: str, sherpa_name: str = Depends(dpd.get_sherpa)
):
    allowed = True
    if not sherpa_name:
        dpd.raise_error("Unknown requester", 401)

    with DBSession(pool=True) as dbsession:
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


@router.get(
    "/verify_fleet_files",
    response_model=rqm.VerifyFleetFilesResp,
    dependencies=[Depends(RateLimiter(times=4, seconds=60))],
)
async def verify_fleet_files(sherpa: str = Depends(dpd.get_sherpa)):
    import utils.fleet_utils as fu

    response = {}

    if sherpa is None:
        dpd.raise_error("Unknown requester", 401)

    logging.getLogger().info(f"Got a verify fleet files request from {sherpa}")

    with DBSession(pool=True) as dbsession:
        sherpa: fm.Sherpa = dbsession.get_sherpa(sherpa)
        fleet_name = sherpa.fleet.name
        map_files = dbsession.get_map_files(fleet_name)

        map_file_info = [
            rqm.MapFileInfo(file_name=mf.filename, hash=mf.file_hash) for mf in map_files
        ]

        reset_fleet = fu.is_reset_fleet_required(fleet_name, map_files)
        if reset_fleet:
            update_map_msg = f"Map files of fleet: {fleet_name} has been modified, please update the map by pressing the update_map button on the webpage header!"
            log_level = mm.NotificationLevels.alert
            module = mm.NotificationModules.generic
            utils_util.maybe_add_notification(
                dbsession, [fleet_name], update_map_msg, log_level, module
            )

        response: rqm.VerifyFleetFilesResp = rqm.VerifyFleetFilesResp(
            fleet_name=fleet_name, files_info=map_file_info
        )

        logging.getLogger().info(f"sent a verify fleet files response to {sherpa.name}")

    return response


@router.post("/req_ack/{req_id}")
async def ws_ack(req: rqm.WSResp, req_id: str):
    with redis.from_url(os.getenv("FM_REDIS_URI")) as redis_conn:
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
    with DBSession(pool=True) as dbsession:
        sherpa_obj = dbsession.get_sherpa(sherpa)
        alert = f"Got an alert from {sherpa}, "

        module = mm.NotificationModules.generic
        if alert_msg.trolley_load_cell:
            alert = alert + alert_msg.trolley_load_cell
            module = mm.NotificationModules.trolley
        elif alert_msg.low_battery_alarm:
            alert = alert + alert_msg.low_battery_alarm
        elif alert_msg.obstructed:
            alert = alert + alert_msg.obstructed
            module = mm.NotificationModules.stoppages
        elif alert_msg.emergency_button:
            alert = alert + alert_msg.emergency_button
        elif alert_msg.user_pause:
            alert = alert + alert_msg.user_pause
        else:
            dpd.raise_error("Invalid alert msg")
        utils_util.maybe_add_notification(
            dbsession,
            [sherpa_obj.name, sherpa_obj.fleet.name, sherpa_obj.fleet.customer],
            alert,
            mm.NotificationLevels.alert,
            module,
        )


@router.post("/upload_file")
async def upload_file(
    file_upload_req: rqm.FileUploadReq = Depends(),
    uploaded_file: UploadFile = File(...),
    sherpa_name: str = Depends(dpd.get_sherpa),
):
    logging.getLogger("uvicorn").info(f"{file_upload_req}")

    response = []
    if not sherpa_name:
        dpd.raise_error("Unknown requester", 401)

    with DBSession(pool=True) as dbsession:
        sherpa = dbsession.get_sherpa(sherpa_name)
        fleet_name = sherpa.fleet.name

        dir_to_save = os.path.join(
            os.getenv("FM_STATIC_DIR"), "sherpa_uploads", fleet_name, file_upload_req.type
        )

        if not os.path.exists(dir_to_save):
            os.makedirs(dir_to_save)

        new_file_name = file_upload_req.filename
        file_path = os.path.join(dir_to_save, new_file_name)
        try:
            with open(file_path, "wb") as f:
                f.write(await uploaded_file.read())

            logging.getLogger("uvicorn").info(f"Uploaded file:{file_path} successfully")

            file_upload = dbsession.get_file_upload(new_file_name)

            if file_upload:
                file_upload.path = file_path
                file_upload.type = file_upload_req.type
                file_upload.fm_incident_id = file_upload_req.fm_incident_id
                file_upload.uploaded_by = sherpa_name
            else:
                file_upload = mm.FileUploads(
                    filename=new_file_name,
                    path=file_path,
                    type=file_upload_req.type,
                    fm_incident_id=file_upload_req.fm_incident_id,
                    uploaded_by=sherpa_name,
                )
                dbsession.add_to_session(file_upload)

        except Exception as e:
            dpd.raise_error(f"Couldn't upload file: {file_path}, exception: {e}")

        finally:
            uploaded_file.file.close()

        if file_upload_req.type == "diagnostics":
            diagnostics_msg = f"New diagnostics data uploaded by {sherpa_name}"
            log_level = mm.NotificationLevels.alert
            module = mm.NotificationModules.generic
            utils_util.maybe_add_notification(
                dbsession, [fleet_name], diagnostics_msg, log_level, module
            )

        response.append(file_path)

    return response


@router.post("/add_fm_incidents")
async def add_fm_incident(
    add_fm_incident_req: rqm.AddFMIncidentReq, sherpa: str = Depends(dpd.get_sherpa)
):
    response = {}
    if not sherpa:
        dpd.raise_error("Unknown requester", 401)

    with DBSession(pool=True) as dbsession:
        if add_fm_incident_req.type not in mm.FMIncidentTypes:
            dpd.raise_error(
                f"Will only accept incidents of type {mm.FMIncidentTypes} requester"
            )

        fm_incident = mm.FMIncidents(
            type=add_fm_incident_req.type,
            code=add_fm_incident_req.code,
            incident_id=add_fm_incident_req.incident_id,
            entity_name=sherpa,
            module=add_fm_incident_req.module,
            sub_module=add_fm_incident_req.sub_module,
            message=add_fm_incident_req.message,
            display_message=add_fm_incident_req.display_message,
            recovery_message=add_fm_incident_req.recovery_message,
            data_uploaded=add_fm_incident_req.data_uploaded,
            data_path=add_fm_incident_req.data_path,
            other_info=add_fm_incident_req.other_info,
        )
        dbsession.add_to_session(fm_incident)

    return response


@router.post("/update_fm_incident_data_details")
async def update_fm_incident_data_details(
    update_incident_data_details_req: rqm.UpdateIncidentDataDetailsReq,
    sherpa: str = Depends(dpd.get_sherpa),
):
    response = {}

    if not sherpa:
        dpd.raise_error("Unknown requester", 401)

    with DBSession(pool=True) as dbsession:
        fm_incident = dbsession.get_fm_incident(
            update_incident_data_details_req.incident_id
        )

        if fm_incident is None:
            dpd.raise_error(
                f"no fm incident found with unique id: {update_incident_data_details_req.incident_id}"
            )

        # update other info
        if update_incident_data_details_req.other_info:
            if fm_incident.other_info is None:
                fm_incident.other_info = {}

            fm_incident.other_info.update(update_incident_data_details_req.other_info)
            flag_modified(fm_incident, "other_info")

        fm_incident.data_uploaded = update_incident_data_details_req.data_uploaded
        fm_incident.data_path = update_incident_data_details_req.data_path

    return response
