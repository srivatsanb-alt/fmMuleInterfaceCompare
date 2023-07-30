import asyncio
import datetime
import logging
from fastapi import APIRouter, WebSocket, Depends
from plugins.plugin_comms import ws_reader, ws_writer, send_req_to_FM
from utils.util import are_poses_close
from .ies_handler import IES_HANDLER
import plugins.ies.ies_request_models as irqm
import app.routers.dependencies as dpd
import plugins.ies.ies_models as im
import plugins.ies.ies_utils as iu
from plugins.plugin_rq import enqueue, get_job_result, get_redis_conn
import plugin_comms as pcomms
from rq import Queue

router = APIRouter()


@router.get("/plugin_ies")
async def check_connection():
    return {"uvicorn": "I Am Alive"}


@router.post("/plugin/ies/add_edit_ies_station")
async def add_ies_station(
    info: irqm.IesStation, user_name=Depends(dpd.get_user_from_header)
):
    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    response = {}
    q = Queue("plugin_ies", connection=get_redis_conn())
    ies_handler = IES_HANDLER()
    msg = {
        "messageType": "add_ies_station",
        "ati_name": info.ati_name,
        "ies_name": info.ies_name,
    }
    job = enqueue(q, ies_handler.handle, msg)
    response = await get_job_result(job.id)
    return {}


@router.get("/plugin/ies/all_ies_stations")
async def get_all_ies_stations(user_name=Depends(dpd.get_user_from_header)):
    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    response = {}
    with im.DBSession() as dbsession:
        all_ies_stations = dbsession.session.query(im.IESStations).all()
        for station in all_ies_stations:
            response.update({station.ati_name: station.ies_name})

    return response


@router.delete("/plugin/ies/delete_ies_station/{ati_station_name}")
async def delete_ies_station(
    ati_station_name: str, user_name=Depends(dpd.get_user_from_header)
):
    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    with im.DBSession() as dbsession:
        ies_station = (
            dbsession.session.query(im.IESStations)
            .filter(im.IESStations.ati_name == ati_station_name)
            .one_or_none()
        )

        if ies_station is None:
            dpd.raise_error(f"{ati_station_name} is not an IES station")

        logging.info(f"deleting ies station {ies_station.ati_name}")
        dbsession.session.delete(ies_station)
    return {}


@router.get("/plugin/ies/get_sherpas_at_start")
async def get_sherpas_at_start(user_name=Depends(dpd.get_user_from_header)):
    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    logging.info(f"getting sherpas at start...")
    response = {}
    with im.DBSession() as dbsession:
        ies_sherpas = dbsession.get_all_ies_sherpas()
        all_ies_routes = dbsession.get_all_ies_routes()

    for sherpa_name in ies_sherpas:
        sherpa_summary_response = iu.get_sherpa_summary_for_sherpa(sherpa_name)
        sherpa_at_station = sherpa_summary_response.get("at_station")
        if sherpa_at_station == None:
            continue
        fleet_name = sherpa_summary_response["fleet_name"]
        for route_tag, route in all_ies_routes.items():
            start_station = route[0]
            sherpa_exclude_stations = iu.get_exclude_stations_sherpa(
                sherpa_name, fleet_name
            )
            if (
                sherpa_at_station == start_station
                and len(set(sherpa_exclude_stations).intersection(set(route))) == 0
            ):
                response.update({route_tag: {"sherpa": sherpa_name, "station": route[0]}})
    return response


@router.post("/plugin/ies/enable_disable_sherpa")
async def enable_disable_sherpa(
    req: irqm.EnableDisableSherpaReq, user_name=Depends(dpd.get_user_from_header)
):
    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    response = {}
    plugin_name = "ies"
    endpoint = "update_sherpa_metadata"
    req_type = "post"

    metadata = {"ies": f"{req.enable}"}
    req_json = {"sherpa_name": req.sherpa_name, "info": metadata}
    status_code, response = send_req_to_FM(plugin_name, endpoint, req_type, req_json)
    if status_code != 200:
        dpd.raise_error(f"can't update sherpa metadata for sherpa {req.sherpa_name}")
    with im.DBSession() as dbsession:
        dbsession.modify_ies_info(req.sherpa_name, req.enable)

    return response


@router.post("/plugin/ies/enable_disable_route")
async def enable_disable_route(
    req: irqm.EnableDisableRouteReq, user_name=Depends(dpd.get_user_from_header)
):
    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    response = {}
    plugin_name = "ies"
    endpoint = "update_saved_route_info"
    req_type = "post"
    other_info = {"ies": f"{req.enable}", "can_edit": f"{not req.enable}"}
    req_json = {"tag": req.tag, "other_info": other_info}
    status_code, response = send_req_to_FM(plugin_name, endpoint, req_type, req_json)
    if status_code != 200:
        dpd.raise_error(f"can't update saved route info for route {req.tag}")

    with im.DBSession() as dbsession:
        dbsession.modify_ies_routes(req.tag, req.enable)

    return response


@router.get("/plugin/ies/get_ies_routes")
async def get_ies_routes(user_name=Depends(dpd.get_user_from_header)):
    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    with im.DBSession() as dbsession:
        all_ies_routes = dbsession.get_all_ies_routes()

    return all_ies_routes


@router.get("/plugin/ies/get_ies_sherpas")
async def get_ies_sherpas(user_name=Depends(dpd.get_user_from_header)):
    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    with im.DBSession() as dbsession:
        all_ies_sherpas = dbsession.get_all_ies_sherpas()
    return all_ies_sherpas


@router.post("/plugin/ies/consolidation_info")
async def consolidation_info(
    consolidation_info_req: irqm.ConsolidationInfoReq,
    user_name=Depends(dpd.get_user_from_header),
):
    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    response = {}
    booked_till = iu.str_to_dt(consolidation_info_req.booked_till)
    booked_from = iu.str_to_dt(consolidation_info_req.booked_from)
    with im.DBSession() as dbsession:
        filtered_bookings = dbsession.get_consolidation_info(
            consolidation_info_req.start_station,
            consolidation_info_req.route_tag,
            booked_from,
            booked_till,
        )
        for booking in filtered_bookings:
            response.update(
                {
                    booking.ext_ref_id: {
                        "kanban_id": booking.kanban_id,
                        "route": booking.route,
                        "requested_at": iu.dt_to_str(booking.created_at),
                        "material_no": booking.other_info["material_no"],
                        "quantity": booking.other_info["quantity"],
                    }
                }
            )
    return response


@router.post("/plugin/ies/consolidate_and_book_trip")
async def consolidate_and_book_trip(
    consolidate_book_req: irqm.ConsolidateBookReq,
    user_name=Depends(dpd.get_user_from_header),
):
    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    response = {}
    if len(consolidate_book_req.ext_ref_ids) == 0:
        dpd.raise_error("please select atleast one entry to consolidate", 400)

    q = Queue("plugin_ies", connection=get_redis_conn())
    ies_handler = IES_HANDLER()
    msg = {
        "messageType": "book_consolidated_trip",
        "ext_ref_ids": consolidate_book_req.ext_ref_ids,
        "route_tag": consolidate_book_req.route_tag,
        "sherpa": consolidate_book_req.sherpa,
    }
    job = enqueue(q, ies_handler.handle, msg)
    response = await get_job_result(job.id)
    return {}


@router.post("/plugin/ies/get_pending_jobs")
async def get_pending_jobs(
    pending_jobs_req: irqm.JobsReq, user_name=Depends(dpd.get_user_from_header)
):
    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    booked_till = iu.str_to_dt(pending_jobs_req.booked_till)
    booked_from = iu.str_to_dt(pending_jobs_req.booked_from)
    response = {}
    with im.DBSession() as dbsession:
        pending_jobs = dbsession.get_pending_jobs(booked_from, booked_till)
        for job in pending_jobs:
            response.update(
                {
                    job.ext_ref_id: {
                        "kanban_id": job.kanban_id,
                        "route_tag": job.route_tag,
                        "route": job.route,
                        "requested_at": iu.dt_to_str(job.created_at),
                        "material_no": job.other_info["material_no"],
                        "quantity": job.other_info["quantity"],
                    }
                }
            )
    return response


@router.post("/plugin/ies/get_consolidated_jobs/{active}")
async def get_consolidated_jobs(
    active: bool,
    consolidated_jobs_req: irqm.JobsReq,
    user_name=Depends(dpd.get_user_from_header),
):
    if not user_name:
        dpd.raise_error("Unknown requester", 401)
    booked_till = iu.str_to_dt(consolidated_jobs_req.booked_till)
    booked_from = iu.str_to_dt(consolidated_jobs_req.booked_from)
    logging.getLogger("plugin_ies").info(
        f"from: {iu.dt_to_str(booked_from)}, till: {iu.dt_to_str(booked_till)}"
    )
    response = {}
    with im.DBSession() as dbsession:
        if active:
            jobs = dbsession.get_ongoing_jobs(booked_from, booked_till)
        else:
            jobs = dbsession.get_completed_jobs(booked_from, booked_till)
            logging.getLogger("plugin_ies").info(f"len of resp. {len(jobs)}")
        for job in jobs:
            response.update(
                {
                    job.ext_ref_id: {
                        "kanban_id": job.kanban_id,
                        "route_tag": job.route_tag,
                        "route": job.route,
                        "requested_at": iu.dt_to_str(job.created_at),
                        "status": job.status,
                        "trip_id": job.combined_trip_id,
                        "material_no": job.other_info["material_no"],
                        "quantity": job.other_info["quantity"],
                    }
                }
            )
    return response


@router.post("/plugin/ies/cancel_pending_jobs")
async def cancel_pending_jobs(
    CancelPendingReq: irqm.CancelPendingReq, user_name=Depends(dpd.get_user_from_header)
):
    if not user_name:
        dpd.raise_error("Unknown requester", 401)

    q = Queue("plugin_ies", connection=get_redis_conn())
    ies_handler = IES_HANDLER()
    msg = {
        "messageType": "JobCancelFromUser",
        "externalReferenceIds": CancelPendingReq.externalReferenceIds,
    }
    job = enqueue(q, ies_handler.handle, msg)
    res = get_job_result(job.id)

    return {}


@router.websocket(
    "/ws/api/v1/plugin/ies/03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4"
)
async def ies_ws(websocket: WebSocket):
    await websocket.accept()
    ies_handler = IES_HANDLER()

    rw = [
        asyncio.create_task(ws_reader(websocket, "ies", ies_handler)),
        asyncio.create_task(
            ws_writer(websocket, "ies"),
        ),
    ]

    try:
        await asyncio.gather(*rw)
    finally:
        [t.cancel() for t in rw]
