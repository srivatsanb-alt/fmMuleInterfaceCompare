import aioredis
import os
import json
from typing import Union

# ati code imports
from core.constants import FleetStatus, DisabledReason
from fastapi import APIRouter, Depends
from models.db_session import DBSession
import models.request_models as rqm
import models.fleet_models as fm
import app.routers.dependencies as dpd
from utils.comms import send_async_req_to_sherpa
import models.misc_models as mm
from utils.rq_utils import Queues
import core.common as ccm


router = APIRouter(
    prefix="/api/v1/control",
    tags=["control"],
    responses={404: {"description": "Not found"}},
)

# returns the sherpa status(name, assigned, initialized, idle, disabled, inducted, etc.)
@router.get("/sherpa/{entity_name}/diagnostics")
async def diagnostics(
    entity_name=Union[str, None],
    user_name=Depends(dpd.get_user_from_header),
):

    response = {}

    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    if not entity_name:
        dpd.raise_error("No entity name")

    with DBSession(engine=ccm.engine) as dbsession:
        sherpa_status = dbsession.get_sherpa_status(entity_name)
        if not sherpa_status:
            dpd.raise_error("Bad sherpa name")

        req = rqm.DiagnosticsReq(sherpa_name=entity_name)
        response = await send_async_req_to_sherpa(dbsession, sherpa_status.sherpa, req)

    return response


# returns the sherpa status(name, assigned, initialized, idle, disabled, inducted, etc.)
@router.get("/sherpa/{entity_name}/quick_diagnostics")
async def quick_diagnostics(
    entity_name=Union[str, None],
    user_name=Depends(dpd.get_user_from_header),
):

    response = {}

    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    if not entity_name:
        dpd.raise_error("No entity name")

    with DBSession(engine=ccm.engine) as dbsession:
        sherpa_status = dbsession.get_sherpa_status(entity_name)
        if not sherpa_status:
            dpd.raise_error("Bad sherpa name")

        req = rqm.QuickDiagnosticsReq(sherpa_name=entity_name)
        response = await send_async_req_to_sherpa(dbsession, sherpa_status.sherpa, req)

    return response


# restarts the mule docker container.
@router.get("/sherpa/{entity_name}/restart_mule_docker")
async def restart_mule_docker(
    entity_name=Union[str, None],
    user_name=Depends(dpd.get_user_from_header),
):

    response = {}

    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    if not entity_name:
        dpd.raise_error("No entity name")

    with DBSession(engine=ccm.engine) as dbsession:
        sherpa_status = dbsession.get_sherpa_status(entity_name)
        req = {"endpoint": "restart_mule_docker", "source": user_name}
        response = await send_async_req_to_sherpa(dbsession, sherpa_status.sherpa, req)

    return response


# restarts the powercycle
@router.get("/sherpa/{entity_name}/powercycle")
async def powercycle(
    entity_name=Union[str, None],
    user_name=Depends(dpd.get_user_from_header),
):

    response = {}

    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    if not entity_name:
        dpd.raise_error("No entity name")

    with DBSession(engine=ccm.engine) as dbsession:
        sherpa_status = dbsession.get_sherpa_status(entity_name)
        req = {"endpoint": "powercycle", "source": user_name}
        response = await send_async_req_to_sherpa(dbsession, sherpa_status.sherpa, req)

    return response


# updates sherpa docker image
@router.get("/sherpa/{entity_name}/update_sherpa_img")
async def update_sherpa_img(
    entity_name=Union[str, None],
    user_name=Depends(dpd.get_user_from_header),
):

    response = {}

    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    if not entity_name:
        dpd.raise_error("No entity name")

    with DBSession(engine=ccm.engine) as dbsession:
        sherpa_status = dbsession.get_sherpa_status(entity_name)
        update_image_req = rqm.SherpaImgUpdateCtrlReq(sherpa_name=entity_name)
        _ = await dpd.process_req_with_response(None, update_image_req, user_name)

    return response


# starts or stops the fleet
@router.post("/fleet/start_stop")
async def start_stop(
    start_stop_ctrl_req: rqm.StartStopCtrlReq,
    user_name=Depends(dpd.get_user_from_header),
):

    response = {}

    if not user_name:
        dpd.raise_error("Unknown requester", 401)
    response = await dpd.process_req_with_response(None, start_stop_ctrl_req, user_name)

    return response


# to emergency stop the fleet
@router.post("/fleet/{entity_name}/emergency_stop")
async def emergency_stop(
    pause_resume_ctrl_req: rqm.PauseResumeCtrlReq,
    entity_name=Union[str, None],
    user_name=Depends(dpd.get_user_from_header),
):

    response = {}

    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    if not entity_name:
        dpd.raise_error("No entity name")

    with DBSession(engine=ccm.engine) as dbsession:
        fleet: fm.Fleet = dbsession.get_fleet(entity_name)
        if not fleet:
            dpd.raise_error("Fleet not found")

        fleet.status = (
            FleetStatus.PAUSED if pause_resume_ctrl_req.pause else FleetStatus.STOPPED
        )

        if not pause_resume_ctrl_req.pause:
            alert_description = f"To start operations of fleet: {entity_name}, press start ops button in the web page header"
            dbsession.add_notification(
                [entity_name],
                alert_description,
                mm.NotificationLevels.alert,
                mm.NotificationModules.generic,
            )

        all_sherpa_status = dbsession.get_all_sherpa_status()
        sherpa_status_fleet = []
        for ss in all_sherpa_status:
            if ss.sherpa.fleet.name == entity_name:
                sherpa_status_fleet.append(ss)

        unconnected_sherpas = []
        for sherpa_status in sherpa_status_fleet:
            if sherpa_status.disabled_reason == DisabledReason.STALE_HEARTBEAT:
                unconnected_sherpas.append([sherpa_status.sherpa_name, "stale heartbeat"])
                continue

            sherpa_status.disabled = pause_resume_ctrl_req.pause
            if pause_resume_ctrl_req.pause:
                sherpa_status.disabled_reason = DisabledReason.EMERGENCY_STOP
            else:
                sherpa_status.disabled_reason = None

            pause_resume_req = rqm.PauseResumeReq(
                pause=pause_resume_ctrl_req.pause, sherpa_name=sherpa_status.sherpa_name
            )

            try:
                _ = await dpd.process_req_with_response(None, pause_resume_req, user_name)
            except Exception as e:
                unconnected_sherpas.append([sherpa_status.sherpa_name, e])

        if len(unconnected_sherpas) == len(sherpa_status_fleet):
            dpd.raise_error(
                "failed to pass the emergency_stop request to any of the sherpas"
            )

    return response


# to emergency stop the sherpa
@router.post("/sherpa/{entity_name}/emergency_stop")
async def sherpa_emergency_stop(
    pause_resume_ctrl_req: rqm.PauseResumeCtrlReq,
    entity_name: str,
    user_name=Depends(dpd.get_user_from_header),
):

    response = {}

    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    if not entity_name:
        dpd.raise_error("No entity name")

    with DBSession(engine=ccm.engine) as dbsession:
        sherpa_status: fm.SherpaStatus = dbsession.get_sherpa_status(entity_name)
        if not sherpa_status:
            dpd.raise_error("Bad sherpa name")

        fleet_name = sherpa_status.sherpa.fleet.name
        fleet_status = dbsession.get_fleet(fleet_name)

        if fleet_status.status == FleetStatus.PAUSED:
            dpd.raise_error("Resume fleet to resume/pause sherpa")

        sherpa_status.disabled = pause_resume_ctrl_req.pause
        if pause_resume_ctrl_req.pause:
            sherpa_status.disabled_reason = DisabledReason.EMERGENCY_STOP
        else:
            sherpa_status.disabled_reason = None

        pause_resume_req = rqm.PauseResumeReq(
            pause=pause_resume_ctrl_req.pause, sherpa_name=entity_name
        )

    _ = await dpd.process_req_with_response(None, pause_resume_req, user_name)

    return response


# switches mode of the sherpa - (various modes - manual, fleet, remote, simulation etc)
@router.post("/sherpa/{entity_name}/switch_mode")
async def switch_mode(
    switch_mode_ctrl_req: rqm.SwitchModeCtrlReq,
    entity_name=Union[str, None],
    user_name=Depends(dpd.get_user_from_header),
):

    response = {}

    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    if not entity_name:
        dpd.raise_error("No entity name")

    with DBSession(engine=ccm.engine) as dbsession:
        sherpa_status = dbsession.get_sherpa_status(entity_name)

        if not sherpa_status:
            dpd.raise_error("Bad sherpa name")

        switch_mode_req = rqm.SwitchModeReq(
            mode=switch_mode_ctrl_req.mode, sherpa_name=entity_name
        )

    _ = await dpd.process_req_with_response(None, switch_mode_req, user_name)

    return response


# resets the position of sherpa to the station specified by the user
@router.post("/sherpa/{entity_name}/recovery")
async def reset_pose(
    reset_pose_ctrl_req: rqm.ResetPoseCtrlReq,
    entity_name=Union[str, None],
    user_name=Depends(dpd.get_user_from_header),
):

    response = {}

    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    if not entity_name:
        dpd.raise_error("No entity name")

    if not reset_pose_ctrl_req.fleet_station:
        dpd.raise_error("No fleet staion detail")

    with DBSession(engine=ccm.engine) as dbsession:
        sherpa_status = dbsession.get_sherpa_status(entity_name)
        if not sherpa_status:
            dpd.raise_error("Bad sherpa name")

        station = dbsession.get_station(reset_pose_ctrl_req.fleet_station)

        if not station:
            dpd.raise_error("Bad fleet staion detail")

        reset_pose_req = rqm.ResetPoseReq(
            pose=station.pose,
            station_name=reset_pose_ctrl_req.fleet_station,
            sherpa_name=entity_name,
        )

    _ = await dpd.process_req_with_response(None, reset_pose_req, user_name)

    return response


# inducts sherpa into the fleet
# trips not assigned otherwise
@router.post("/sherpa/{sherpa_name}/induct")
async def induct_sherpa(
    sherpa_name: str,
    sherpa_induct_req: rqm.SherpaInductReq,
    user_name=Depends(dpd.get_user_from_header),
):
    respone = {}
    sherpa_induct_req.sherpa_name = sherpa_name

    with DBSession(engine=ccm.engine) as dbsession:
        sherpa = dbsession.get_sherpa(sherpa_name)

        if sherpa is None:
            dpd.raise_error(f"Invalid sherpa name: {sherpa_name}")

        if sherpa.status.pose is None:
            dpd.raise_error(
                f"Cannot induct a {sherpa_name} into fleet, sherpa pose is None"
            )

        if sherpa.status.trip_id and not sherpa_induct_req.induct:
            trip = dbsession.get_trip(sherpa.status.trip_id)
            dpd.raise_error(
                f"delete the ongoing trip with booking_id: {trip.booking_id}, to induct {sherpa_name} out of fleet"
            )

    _ = await dpd.process_req_with_response(None, sherpa_induct_req, user_name)

    return respone


@router.get("/restart_fleet_manager")
async def restart_fm(user_name=Depends(dpd.get_user_from_header)):
    response = {}
    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    async with aioredis.Redis.from_url(os.getenv("FM_REDIS_URI")) as aredis_conn:
        await aredis_conn.set("restart_fm", json.dumps(True))

    return response


@router.get("/manual_park/{sherpa_name}/{activate}")
async def manual_park(
    activate: bool, sherpa_name: str, user_name=Depends(dpd.get_user_from_header)
):
    response = {}
    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    activate_parking_mode_req = rqm.ActivateParkingMode(
        activate=activate, sherpa_name=sherpa_name
    )
    response = await dpd.process_req_with_response(
        None, activate_parking_mode_req, user_name
    )

    return response


@router.post("/manual_visa_release")
async def resource_release(
    resource_release_req: rqm.ManualVisaReleaseReq, user_name=Depends(dpd.get_user_from_header)
):
    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    queues = Queues.queues_dict["resource_handler"]
    response = await dpd.process_req_with_response(queues, resource_release_req, resource_release_req.sherpa_name)
    
    return response
