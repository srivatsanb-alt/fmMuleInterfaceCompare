import time
from app.routers.dependencies import (
    get_sherpa,
    process_req,
    process_req_with_response,
)
from models.db_session import DBSession
from models.misc_models import NotificationModules, NotificationLevels
from models.request_models import (
    InitMsg,
    ReachedReq,
    ResourceReq,
    ResourceResp,
    SherpaPeripheralsReq,
    SherpaReq,
    VerifyFleetFilesResp,
    SherpaAlertMsg,
)
from fastapi import Depends, APIRouter
from utils.rq_utils import Queues

router = APIRouter(
    prefix="/api/v1/sherpa",
    tags=["sherpa"],
    # dependencies=[Depends(get_sherpa)],
    responses={404: {"description": "Not found"}},
)


@router.get("/check_connection")
async def check_connection():
    return {"uvicorn": "I am alive"}


@router.post("/init")
async def init_sherpa(init_msg: InitMsg, sherpa: str = Depends(get_sherpa)):
    process_req(None, init_msg, sherpa)


@router.post("/trip/reached")
async def reached(reached_msg: ReachedReq, sherpa: str = Depends(get_sherpa)):
    process_req(None, reached_msg, sherpa)


@router.post("/peripherals")
async def peripherals(
    peripherals_req: SherpaPeripheralsReq, sherpa: str = Depends(get_sherpa)
):
    process_req(None, peripherals_req, sherpa)


@router.post("/access/resource", response_model=ResourceResp)
async def resource_access(resource_req: ResourceReq, sherpa: str = Depends(get_sherpa)):
    queue = Queues.queues_dict["resource_handler"]
    response = process_req_with_response(queue, resource_req, sherpa)
    return ResourceResp.from_json(response)


@router.get("/verify_fleet_files", response_model=VerifyFleetFilesResp)
async def verify_fleet_files(sherpa: str = Depends(get_sherpa)):
    response = process_req_with_response(
        None, SherpaReq(type="verify_fleet_files", timestamp=time.time()), sherpa
    )
    return VerifyFleetFilesResp.from_json(response)


@router.post("/alerts")
async def sherpa_alerts(alert_msg: SherpaAlertMsg, sherpa: str = Depends(get_sherpa)):
    with DBSession() as dbsession:
        sherpa_obj = dbsession.get_sherpa(sherpa)
        alert = f"Got an alert from {sherpa}, "
        if alert_msg.trolley_load_cell:
            alert_msg = alert + alert_msg.trolley_load_cell
        dbsession.add_notification(
            [sherpa_obj.name, sherpa_obj.fleet.name],
            alert_msg,
            NotificationLevels.action_request,
            NotificationModules.generic,
        )
