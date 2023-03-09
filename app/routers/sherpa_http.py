import time
import redis
import json
import os
from models.db_session import DBSession
import models.misc_models as mm
import models.request_models as rqm
from fastapi import Depends, APIRouter
from utils.rq_utils import Queues
from app.routers.dependencies import (
    get_sherpa,
    process_req,
    process_req_with_response,
)

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


# initiates sherpa
@router.post("/init")
async def init_sherpa(init_msg: rqm.InitMsg, sherpa: str = Depends(get_sherpa)):
    process_req(None, init_msg, sherpa)


# checks if sherpa has reached to its destination and completed its trip
@router.post("/trip/reached")
async def reached(reached_msg: rqm.ReachedReq, sherpa: str = Depends(get_sherpa)):
    process_req(None, reached_msg, sherpa)


@router.post("/peripherals")
async def peripherals(
    peripherals_req: rqm.SherpaPeripheralsReq, sherpa: str = Depends(get_sherpa)
):
    process_req(None, peripherals_req, sherpa)


@router.post("/access/resource", response_model=rqm.ResourceResp)
async def resource_access(resource_req: rqm.ResourceReq, sherpa: str = Depends(get_sherpa)):
    queue = Queues.queues_dict["resource_handler"]
    response = await process_req_with_response(queue, resource_req, sherpa)
    return rqm.ResourceResp.from_json(response)


@router.get("/verify_fleet_files", response_model=rqm.VerifyFleetFilesResp)
async def verify_fleet_files(sherpa: str = Depends(get_sherpa)):
    response = await process_req_with_response(
        None, rqm.SherpaReq(type="verify_fleet_files", timestamp=time.time()), sherpa
    )
    return rqm.VerifyFleetFilesResp.from_json(response)


@router.post("/req_ack/{req_id}")
async def ws_ack(req: rqm.WSResp, req_id: str):
    redis_conn = redis.from_url(os.getenv("FM_REDIS_URI"))
    redis_conn.set(f"success_{req_id}", json.dumps(req.success))
    if req.success:
        if req.response is None:
            req.response = {}
        redis_conn.set(f"response_{req_id}", json.dumps(req.response))
    return {}


# alerts the FM with messages from Sherpa
@router.post("/alerts")
async def sherpa_alerts(alert_msg: rqm.SherpaAlertMsg, sherpa: str = Depends(get_sherpa)):
    with DBSession() as dbsession:
        sherpa_obj = dbsession.get_sherpa(sherpa)
        alert = f"Got an alert from {sherpa}, "
        if alert_msg.trolley_load_cell:
            alert_msg = alert + alert_msg.trolley_load_cell
        if alert_msg.low_battery_alarm:
            alert_msg = alert + alert_msg.low_battery_alarm
        if alert_msg.obstructed:
            alert_msg = alert + alert_msg.obstructed
        if alert_msg.emergency_button:
            alert_msg = alert + alert_msg.emergency_button
        if alert_msg.user_pause:
            alert_msg = alert + alert_msg.user_pause
        dbsession.add_notification(
            [sherpa_obj.name, sherpa_obj.fleet.name],
            alert_msg,
            mm.NotificationLevels.action_request,
            mm.NotificationModules.generic,
        )
