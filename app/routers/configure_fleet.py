import os
import logging
from fastapi import APIRouter, Depends
from models.request_models import AddEditSherpaReq, AddFleetReq
from models.frontend_models import FrontendUser
from models.db_session import DBSession
from utils import fleet_utils as fu
import models.fleet_models as fm
import models.misc_models as mm
from app.routers.dependencies import (
    get_user_from_header,
    raise_error,
)
from utils.comms import close_websocket_for_sherpa


# setup logging
log_conf_path = os.path.join(os.getenv("FM_CONFIG_DIR"), "logging.conf")
logging.config.fileConfig(log_conf_path)
logger = logging.getLogger("configure_fleet")


router = APIRouter(
    prefix="/api/v1/configure_fleet",
    responses={404: {"description": "Not found"}},
)


@router.get("/all_sherpa_info")
def get_all_sherpa_info(user_name=Depends(get_user_from_header)):

    if not user_name:
        raise_error("Unknown requester", 401)

    response = {}
    with DBSession() as dbsession:
        all_sherpas = dbsession.get_all_sherpas()
        if all_sherpas:
            for sherpa in all_sherpas:
                response.update(
                    {
                        sherpa.name: {
                            "hwid": sherpa.hwid,
                            "api_key": sherpa.hashed_api_key,
                            "fleet_name": sherpa.fleet.name,
                        }
                    }
                )

    return response


@router.post("/add_edit_sherpa/{sherpa_name}")
def add_edit_sherpa(
    add_edit_sherpa: AddEditSherpaReq,
    sherpa_name: str,
    user_name=Depends(get_user_from_header),
):

    if not user_name:
        raise_error("Unknown requester", 401)

    with DBSession() as dbsession:
        all_sherpa_names = dbsession.get_all_sherpa_names()

        fleet = dbsession.get_fleet(add_edit_sherpa.fleet_name)
        if not fleet:
            raise_error("Unkown fleet")

        fu.SherpaUtils.add_edit_sherpa(
            dbsession,
            sherpa_name,
            hwid=add_edit_sherpa.hwid,
            api_key=add_edit_sherpa.api_key,
            fleet_id=fleet.id,
        )

        if sherpa_name not in all_sherpa_names:
            action_request = f"New sherpa {sherpa_name} has been added to {fleet.name}, please restart FM software using docker-compose commands to start using the sherpa"
            dbsession.add_notification(
                [fleet.name],
                action_request,
                mm.NotificationLevels.action_request,
                mm.NotificationModules.generic,
            )

    return {}


@router.get("/delete_sherpa/{sherpa_name}")
def delete_sherpa(
    sherpa_name: str,
    user_name=Depends(get_user_from_header),
):
    if not user_name:
        raise_error("Unknown requester", 401)

    with DBSession() as dbsession:
        sherpa_status: fm.SherpaStatus = dbsession.get_sherpa_status(sherpa_name)
        if not sherpa_status:
            raise_error(f"Sherpa {sherpa_name} not found")

        if sherpa_status.trip_id:
            trip = dbsession.get_trip(sherpa_status.trip_id)
            raise_error(
                f"delete the ongoing trip with booking_id: {trip.booking_id} and disable {sherpa_status.sherpa_name} for trips to delete the sherpa"
            )

        if sherpa_status.inducted:
            raise_error(
                f"disable {sherpa_status.sherpa_name} for trips to delete the sherpa"
            )

        close_websocket_for_sherpa(sherpa_name)
        fu.SherpaUtils.delete_sherpa(dbsession, sherpa_name)

    return {}


@router.get("/all_fleet_info")
def get_all_fleet_info(user_name=Depends(get_user_from_header)):

    if not user_name:
        raise_error("Unknown requester", 401)

    response = {}
    with DBSession() as dbsession:
        all_fleets = dbsession.get_all_fleets()
        for fleet in all_fleets:
            response.update(
                {
                    fleet.name: {
                        "name": fleet.name,
                        "map_name": fleet.name,
                        "customer": fleet.customer,
                        "site": fleet.site,
                        "location": fleet.location,
                    }
                }
            )

    return response


@router.post("/add_edit_fleet/{fleet_name}")
def add_fleet(
    add_fleet_req: AddFleetReq,
    fleet_name: str,
    user_name=Depends(get_user_from_header),
):
    if not user_name:
        raise_error("Unknown requester", 401)

    with DBSession() as dbsession:
        all_fleets = dbsession.get_all_fleet_names()

        new_fleet = False if fleet_name in all_fleets else True
        fu.FleetUtils.add_map(dbsession, fleet_name)
        fu.FleetUtils.add_fleet(
            dbsession,
            fleet_name,
            add_fleet_req.site,
            add_fleet_req.location,
            add_fleet_req.customer,
        )

        fleet: fm.Fleet = dbsession.get_fleet(fleet_name)
        fu.FleetUtils.update_stations_in_map(dbsession, fleet.name, fleet.id)
        fu.ExclusionZoneUtils.add_exclusion_zones(dbsession, fleet.name)
        fu.ExclusionZoneUtils.add_linked_gates(dbsession, fleet.name)

        if new_fleet:
            action_request = f"New fleet {fleet.name} has been added, please restart FM software using docker-compose commands to start using the fleet"
            dbsession.add_notification(
                [fleet.name],
                action_request,
                mm.NotificationLevels.action_request,
                mm.NotificationModules.generic,
            )

    return {}


@router.get("/delete_fleet/{fleet_name}")
def delete_fleet(
    fleet_name: str,
    user_name=Depends(get_user_from_header),
):
    if not user_name:
        raise_error("Unknown requester", 401)

    with DBSession() as dbsession:
        fleet: fm.Fleet = dbsession.get_fleet(fleet_name)
        if not fleet:
            raise_error("Bad detail invalid fleet name")

        all_ongoing_trips_fleet = dbsession.get_all_ongoing_trips_fleet(fleet_name)
        if len(all_ongoing_trips_fleet):
            raise_error("Cancel all the ongoing trips before deleting the fleet")

        all_fleet_sherpas = dbsession.get_all_sherpas_in_fleet(fleet_name)

        # close ws connection to make sure new map files are downloaded by sherpa on reconnect
        for sherpa in all_fleet_sherpas:
            close_websocket_for_sherpa(sherpa.name)
            if sherpa.status.trip_id:
                trip = dbsession.get_trip(sherpa.status.trip_id)
                raise_error(
                    f"delete the ongoing trip with booking_id: {trip.booking_id} and disable {sherpa.name} for trips to delete the sherpa and fleet"
                )
            if sherpa.status.inducted:
                raise_error(
                    f"disable {sherpa.name} for trips to delete the sherpa and fleet"
                )

            fu.SherpaUtils.delete_sherpa(dbsession, sherpa.name)

        fu.FleetUtils.delete_fleet(dbsession, fleet_name)

    return {}


@router.get("/update_map/{fleet_name}")
def update_map(
    fleet_name: str,
    user_name=Depends(get_user_from_header),
):
    response = {}

    with DBSession() as dbsession:
        fleet: fm.Fleet = dbsession.get_fleet(fleet_name)
        if not fleet:
            raise_error("Bad detail invalid fleet name")

        all_ongoing_trips_fleet = dbsession.get_all_ongoing_trips_fleet(fleet_name)
        if len(all_ongoing_trips_fleet):
            raise_error("Cancel all the ongoing trips before deleting the fleet")

        fu.FleetUtils.add_map(dbsession, fleet_name)
        fu.FleetUtils.update_stations_in_map(dbsession, fleet_name, fleet.id)
        fu.ExclusionZoneUtils.delete_exclusion_zones(dbsession, fleet_name)
        fu.ExclusionZoneUtils.add_exclusion_zones(dbsession, fleet_name)
        fu.ExclusionZoneUtils.add_linked_gates(dbsession, fleet_name)

        all_fleet_sherpas = dbsession.get_all_sherpas_in_fleet(fleet_name)
        # close ws connection to make sure new map files are downloaded by sherpa on reconnect
        for sherpa in all_fleet_sherpas:
            close_websocket_for_sherpa(sherpa.name)

    return response


@router.get("/all_user_info")
def all_user_info(user_name=Depends(get_user_from_header)):

    if not user_name:
        raise_error("Unknown requester", 401)

    response = {}
    with DBSession() as dbsession:
        all_frontend_user = dbsession.session.query(FrontendUser).all()
        for frontenduser in all_frontend_user:
            response.update({frontenduser.name: {"role": frontenduser.role}})

    return response


# @router.get("/delete_user/{name}")
# def delete_user(name: str, user_name=Depends(get_user_from_header)):
#
#     if not user_name:
#         raise_error("Unknown requester", 401)
#
#     response = {}
#     with DBSession() as dbsession:
#         frontenduser = (
#             dbsession.session.query(FrontendUser)
#             .filter(FrontendUser.name == name)
#             .one_or_none()
#         )
#
#         if not frontenduser:
#             raise ValueError("User not found")
#
#         dbsession.session.delete(frontenduser)
#
#     return response
