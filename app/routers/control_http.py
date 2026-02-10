import json
import os
from typing import Union, Optional, Literal
from fastapi.responses import FileResponse
import aioredis
import toml
import logging


# ati code imports
from core.constants import FleetStatus, DisabledReason, SoundVolume
from fastapi import APIRouter, Depends, Request
from models.db_session import DBSession
import models.request_models as rqm
import models.fleet_models as fm
import app.routers.dependencies as dpd
from utils.comms import send_async_req_to_sherpa
import models.misc_models as mm
from utils.rq_utils import Queues
import core.common as ccm
from utils.auth_utils import AuthValidator
import utils.recovery_utils as recovery_utils


router = APIRouter(
    prefix="/api/v1/control",
    tags=["control"],
    responses={404: {"description": "Not found"}},
)

@router.get("/sherpa/{entity_name}/diagnostics")
async def diagnostics(
    entity_name=Union[str, None],
    user=Depends(AuthValidator('fm')),
):

    response = {}

    if not user:
        dpd.raise_error("Unknown requester", 401)

    if not entity_name:
        dpd.raise_error("No entity name")

    try:
        with DBSession(engine=ccm.engine) as dbsession:
            sherpa_status = dbsession.get_sherpa_status(entity_name)
            if not sherpa_status:
                dpd.raise_error("Bad sherpa name")

            req = rqm.DiagnosticsReq(sherpa_name=entity_name)
            response = await send_async_req_to_sherpa(dbsession, sherpa_status.sherpa, req)
            
    except Exception as e:
        dpd.relay_error_details(e)

    return response


# returns the sherpa status(name, assigned, initialized, idle, disabled, inducted, etc.)
@router.get("/sherpa/{entity_name}/quick_diagnostics")
async def quick_diagnostics(
    entity_name=Union[str, None],
    user=Depends(AuthValidator('quick_diagnostics')),
):

    response = {}

    if not user:
        dpd.raise_error("Unknown requester", 401)

    if not entity_name:
        dpd.raise_error("No entity name")
    
    try:
        with DBSession(engine=ccm.engine) as dbsession:
            sherpa_status = dbsession.get_sherpa_status(entity_name)
            if not sherpa_status:
                dpd.raise_error("Bad sherpa name")

            req = rqm.QuickDiagnosticsReq(sherpa_name=entity_name)
            response = await send_async_req_to_sherpa(dbsession, sherpa_status.sherpa, req)

    except Exception as e:
        dpd.relay_error_details(e)

    return response


# restarts the mule docker container.
@router.get("/sherpa/{entity_name}/restart_mule_docker")
async def restart_mule_docker(
    entity_name=Union[str, None],
    user=Depends(AuthValidator('fm')),
):

    response = {}

    if not user:
        dpd.raise_error("Unknown requester", 401)

    if not entity_name:
        dpd.raise_error("No entity name")
    
    user_name = user["user_name"]

    try:
        with DBSession(engine=ccm.engine) as dbsession:
            sherpa_status = dbsession.get_sherpa_status(entity_name)
            req = {"endpoint": "restart_mule_docker", "source": user_name}
            response = await send_async_req_to_sherpa(dbsession, sherpa_status.sherpa, req)

    except Exception as e:
        dpd.relay_error_details(e)
    return response


# restarts the powercycle
@router.get("/sherpa/{entity_name}/powercycle")
async def powercycle(
    entity_name=Union[str, None],
    user=Depends(AuthValidator('fm')),
):

    response = {}

    if not user:
        dpd.raise_error("Unknown requester", 401)

    if not entity_name:
        dpd.raise_error("No entity name")

    user_name = user["user_name"]

    try:
        with DBSession(engine=ccm.engine) as dbsession:
            sherpa_status = dbsession.get_sherpa_status(entity_name)
            req = {"endpoint": "powercycle", "source": user_name}
            response = await send_async_req_to_sherpa(dbsession, sherpa_status.sherpa, req)

    except Exception as e:
        dpd.relay_error_details(e)

    return response


# updates sherpa docker image
@router.get("/sherpa/{entity_name}/update_sherpa_img")
async def update_sherpa_img(
    entity_name=Union[str, None],
    user=Depends(AuthValidator('fm')),
):

    response = {}

    if not user:
        dpd.raise_error("Unknown requester", 401)

    if not entity_name:
        dpd.raise_error("No entity name")

    user_name = user["user_name"]
    
    with DBSession(engine=ccm.engine) as dbsession:
        sherpa_status = dbsession.get_sherpa_status(entity_name)
        update_image_req = rqm.SherpaImgUpdateCtrlReq(sherpa_name=entity_name)
        _ = await dpd.process_req_with_response(None, update_image_req, user_name)

    return response


# starts or stops the fleet
@router.post("/fleet/start_stop")
async def start_stop(
    request: Request,
    start_stop_ctrl_req: rqm.StartStopCtrlReq,
):
    is_maintenance_mode = start_stop_ctrl_req.maintenance
    response = {}
    permission_required = (
        'edit_settings' if is_maintenance_mode else 'fm'
    )
    auth_validator = AuthValidator(permission_required)
    user = await auth_validator(request)
    if not user:
        dpd.raise_error("Unknown requester", 401)
    
    user_name = user["user_name"]
    response = await dpd.process_req_with_response(None, start_stop_ctrl_req, user_name)

    return response


# to emergency stop the fleet
@router.post("/fleet/{entity_name}/emergency_stop")
async def emergency_stop(
    pause_resume_ctrl_req: rqm.PauseResumeCtrlReq,
    entity_name=Union[str, None],
    user=Depends(AuthValidator('fm')),
):

    response = {}

    if not user:
        dpd.raise_error("Unknown requester", 401)

    if not entity_name:
        dpd.raise_error("No entity name")

    user_name = user["user_name"]
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
    user=Depends(AuthValidator('fm')),
):

    response = {}

    if not user:
        dpd.raise_error("Unknown requester", 401)

    if not entity_name:
        dpd.raise_error("No entity name")
    
    user_name = user["user_name"]

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


@router.post("/sherpa/{entity_name}/switch_mode")
async def switch_mode(
    switch_mode_ctrl_req: rqm.SwitchModeCtrlReq,
    entity_name=Union[str, None],
    user=Depends(AuthValidator('fm')),
):
    response = {}

    if not user:
        dpd.raise_error("Unknown requester", 401)
    
    user_name = user["user_name"]

    if not entity_name:
        dpd.raise_error("No entity name")

    user_name = user["user_name"]

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
    user=Depends(AuthValidator('recover')),
):

    response = {}

    if not user:
        dpd.raise_error("Unknown requester", 401)

    if not entity_name:
        dpd.raise_error("No entity name")

    if not reset_pose_ctrl_req.fleet_station:
        dpd.raise_error("No fleet staion detail")
    
    user_name = user["user_name"]

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

@router.post("/sherpa/{entity_name}/reset_pose_vpr")
async def reset_pose_vpr(
    entity_name=Union[str, None],
    user=Depends(AuthValidator('fm')),
):

    response = {}

    if not user:
        dpd.raise_error("Unknown requester", 401)

    if not entity_name:
        dpd.raise_error("No entity name")

    user_name = user["user_name"]

    with DBSession(engine=ccm.engine) as dbsession:
        sherpa_status = dbsession.get_sherpa_status(entity_name)
        if not sherpa_status:
            dpd.raise_error("Bad sherpa name")

    reset_pose_vpr_req = rqm.ResetPoseVPRReq(
        sherpa_name=entity_name,
    )

    _ = await dpd.process_req_with_response(None, reset_pose_vpr_req, user_name)

    return response

@router.post("/sherpa/{entity_name}/auto_recover")
async def auto_recover(
    auto_recover_req: rqm.AutoRecoverReq,
    entity_name: Union[str, None],
    user=Depends(AuthValidator('fm')),
):
    """Handle auto recovery requests for sherpa entities."""
    # Validate inputs
    if not user:
        dpd.raise_error("Unknown requester", 401)
    if not entity_name:
        dpd.raise_error("No entity name")
    
    user_name = user["user_name"]
    async with aioredis.Redis.from_url(os.getenv("FM_REDIS_URI")) as aredis_conn:
        # Get existing request ID from Redis
        existing_req_id = await recovery_utils._get_redis_request_id(aredis_conn, entity_name)
        
        with DBSession(engine=ccm.engine) as dbsession:
            # Validate sherpa exists
            sherpa_status = dbsession.get_sherpa_status(entity_name)
            if not sherpa_status:
                dpd.raise_error("Bad sherpa name")

            # Handle auto recover request based on type
            if auto_recover_req.is_auto_recover:
                # Start auto recovery
                req_id = await recovery_utils._handle_start_auto_recover(
                    aredis_conn, dbsession, entity_name, sherpa_status, existing_req_id
                )
            else:
                # Stop auto recovery
                await recovery_utils._handle_stop_auto_recover(
                    aredis_conn, dbsession, entity_name, sherpa_status, existing_req_id
                )
                req_id = existing_req_id
                
                #TODO: This is a temporary fix to prevent multiple auto recover requests from being sent.
                # We need to remove this once we have a proper auto recover mechanism from frontend.
                if req_id is None:
                    return {}

            # Create and send auto recover message
            auto_recover_msg = rqm.AutoRecoverMsg(
                sherpa_name=entity_name,
                is_auto_recover=auto_recover_req.is_auto_recover,
                req_id=req_id
            )
            
            await dpd.process_req_with_response(None, auto_recover_msg, user_name)

    return {}


# inducts sherpa into the fleet
# trips not assigned otherwise
@router.post("/sherpa/{sherpa_name}/induct")
async def induct_sherpa(
    sherpa_name: str,
    sherpa_induct_req: rqm.SherpaInductReq,
    user=Depends(AuthValidator('enable_for_trips')),
):
    response = {}
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
    user_name = user["user_name"]
    _ = await dpd.process_req_with_response(None, sherpa_induct_req, user_name)

    return response


@router.get("/restart_fleet_manager")
async def restart_fm(user=Depends(AuthValidator('fm'))):
    response = {}
    if not user:
        dpd.raise_error("Unknown requester", 401)

    async with aioredis.Redis.from_url(os.getenv("FM_REDIS_URI")) as aredis_conn:
        await aredis_conn.set("restart_fm", json.dumps(True))

    return response


@router.get("/manual_park/{sherpa_name}/{activate}")
async def manual_park(
    activate: bool, sherpa_name: str, user=Depends(AuthValidator('fm'))
):
    response = {}
    if not user:
        dpd.raise_error("Unknown requester", 401)

    user_name = user["user_name"]
    activate_parking_mode_req = rqm.ActivateParkingMode(
        activate=activate, sherpa_name=sherpa_name
    )
    response = await dpd.process_req_with_response(
        None, activate_parking_mode_req, user_name
    )

    return response


@router.post("/manual_visa_release")
async def manual_visa_release(
    manual_visa_release_req: rqm.ManualVisaReleaseReq,
    user=Depends(AuthValidator('revoke_visa')),
):
    if not user:
        dpd.raise_error("Unknown requester", 401)

    queues = Queues.queues_dict["resource_handler"]
    response = await dpd.process_req_with_response(
        queues, manual_visa_release_req, manual_visa_release_req.revoke_visa_for
    )
    return response

@router.get("/current_sound_setting/{entity_name}")
async def current_sound_setting(
    entity_name=Union[str, None],
    user=Depends(AuthValidator('fm')),
):
    response = {}

    if not user:
        dpd.raise_error("Unknown requester", 401)

    if not entity_name:
        dpd.raise_error("No entity name")
    
    try:
        with DBSession(engine=ccm.engine) as dbsession:
            sherpa_status = dbsession.get_sherpa_status(entity_name)
            if not sherpa_status:
                dpd.raise_error("Bad sherpa name")

            req = rqm.CurrentSoundSettingReq(sherpa_name=entity_name)
            response = await send_async_req_to_sherpa(dbsession, sherpa_status.sherpa, req)

    except Exception as e:
        dpd.relay_error_details(e)

    return response

@router.post("/sound_setting/{entity_name}")
async def sound_setting(
    sound_setting_req: rqm.SoundSettingCtrlReq,
    entity_name=Union[str, None],
    user=Depends(AuthValidator('fm')),
):
    response = {}

    if not user:
        dpd.raise_error("Unknown requester", 401)

    if not entity_name:
        dpd.raise_error("No entity name")

    if SoundVolume.LOW > sound_setting_req.volume or sound_setting_req.volume > SoundVolume.HIGH:
        dpd.raise_error("Invalid volume setting, must be between 0 and 0.1")
    
    with DBSession(engine=ccm.engine) as dbsession:
        sherpa_status = dbsession.get_sherpa_status(entity_name)

        if not sherpa_status:
            dpd.raise_error("Bad sherpa name")

        sound_change_req = rqm.SoundSettingReq(
            sherpa_name=entity_name, volume=sound_setting_req.volume, sound_type=sound_setting_req.sound_type
        )

    user_name = user["user_name"]
    _ = await dpd.process_req_with_response(None, sound_change_req, user_name)

    return response

@router.get("/get_sherpa_config/{sherpa_name}/{map_name}/{file_type}")
async def get_sherpa_config(
    sherpa_name: str,
    map_name: str,
    file_type: Literal["consolidated", "config"] = "config",
    user=Depends(AuthValidator('fm'))
):
    if not user:
        dpd.raise_error("Unknown requester", 401)
        
    # Check if FM_STATIC_DIR is set
    static_dir = os.getenv("FM_STATIC_DIR")
    if not static_dir:
        dpd.raise_error("FM_STATIC_DIR environment variable is not set", 409)
        
    base_path = os.path.join(static_dir, "sherpa_uploads", map_name, "sherpa_config")
    if file_type == "consolidated":
        file_path = os.path.join(base_path, f"consolidated_{sherpa_name}.toml")
    else:
        file_path = os.path.join(base_path, f"config_{sherpa_name}.toml")
        
    if not os.path.exists(file_path):
        dpd.raise_error(f"Configuration file not found for sherpa {sherpa_name} and map {map_name} and file path {file_path}", 409)
        
    with open(file_path, 'r') as f:
        config_data = toml.load(f)
        
    return  config_data

@router.post("/update_sherpa_config")
async def update_sherpa_config(
    sherpa_config_req: rqm.SherpaConfigReq,
    user=Depends(AuthValidator('fm')),
):
    response = {}

    if not user:
        dpd.raise_error("Unknown requester", 401)
        
    with DBSession(engine=ccm.engine) as dbsession:
        sherpa_status = dbsession.get_sherpa_status(sherpa_config_req.sherpa_name)
        if not sherpa_status:
            dpd.raise_error("Bad sherpa name")
        
        user_name = user["user_name"]
        _ = await dpd.process_req_with_response(None, sherpa_config_req, user_name)
        
    return response


@router.post("/get_data_directory_info")
async def get_data_directory_info(
    get_data_directory_info_req: rqm.GetDataDirectoryInfoReq,
    user_name=Depends(AuthValidator('fm')),
):
    response = {}

    if not user_name:
        dpd.raise_error("Unknown requester", 401)
    
    with DBSession(engine=ccm.engine) as dbsession:
        sherpa_status = dbsession.get_sherpa_status(get_data_directory_info_req.sherpa_name)
        if not sherpa_status:
            dpd.raise_error("Bad sherpa name")
        
        req = rqm.GetDataDirectoryInfoReq(
            sherpa_name=get_data_directory_info_req.sherpa_name,
            data_dir=get_data_directory_info_req.data_dir
        )
        
        response = await send_async_req_to_sherpa(dbsession, sherpa_status.sherpa, req)

    return response


@router.post("/send_fm_message")
async def send_fm_message(
    fm_message_req: rqm.FMMessageReq,
    user=Depends(AuthValidator('fm')),
):
    response = {}
    
    if not user:
        dpd.raise_error("Unknown requester", 401)
    
    with DBSession(engine=ccm.engine) as dbsession:
        sherpa_status = dbsession.get_sherpa_status(fm_message_req.sherpa_name)
        if not sherpa_status:
            dpd.raise_error("Bad sherpa name")  
        user_name = user["user_name"]
        _ = await dpd.process_req_with_response(None, fm_message_req, user_name)

    return response

@router.post("/retrieve_data")
async def retrieve_data(
    retrieve_data_req: rqm.RetrieveDataReq,
    user_name=Depends(AuthValidator('fm')),
):
    response = {}
    
    if not user_name:
        dpd.raise_error("Unknown requester", 401)
    
    with DBSession(engine=ccm.engine) as dbsession:
        sherpa_status = dbsession.get_sherpa_status(retrieve_data_req.sherpa_name)
        if not sherpa_status:
            dpd.raise_error("Bad sherpa name") 
        
        response = await send_async_req_to_sherpa(dbsession, sherpa_status.sherpa, retrieve_data_req)

    return response


@router.post("/sherpa/soft_peripherals/{entity_name}")
async def soft_peripherals(
    soft_peripherals_req: rqm.SherpaPeripheralsReq,
    entity_name=Union[str, None],
    user_name=Depends(AuthValidator('fm')),
):
    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    if not entity_name:
        dpd.raise_error("No entity name")
    response = await dpd.process_req_with_response(None, soft_peripherals_req, entity_name)
    return response
