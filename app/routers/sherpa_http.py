import time
import redis
import json
import os
from fastapi import Depends, APIRouter

from models.db_session import DBSession
import models.misc_models as mm
import models.request_models as rqm
from utils.rq_utils import Queues
import app.routers.dependencies as dpd

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


# checks connection of sherpa with fleet manager
@router.get("/is_sherpa_version_compatible/{version}")
async def is_sherpa_version_compatible(version: str, sherpa: str = Depends(dpd.get_sherpa)):

    if not sherpa:
        dpd.raise_error("Unknown requester", 401)

    with DBSession() as dbsession:
        software_compatability = dbsession.get_compatability_info()
        sherpa_versions = software_compatability.info.get("sherpa_versions", [])
        if version not in sherpa_versions:
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


@router.post("/fatal_errors")
async def fatal_errors(err_info: rqm.ErrInfo, sherpa: str = Depends(dpd.get_sherpa)):
    response = {}
    return response


@router.post("/req_ack/{req_id}")
async def ws_ack(req: rqm.WSResp, req_id: str):
    redis_conn = redis.from_url(os.getenv("FM_REDIS_URI"))
    redis_conn.set(f"success_{req_id}", json.dumps(req.success))
    if req.success:
        if req.response is None:
            req.response = {}
        redis_conn.set(f"response_{req_id}", json.dumps(req.response))
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
