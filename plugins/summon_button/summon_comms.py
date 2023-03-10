import asyncio
import hashlib
import logging
from fastapi import APIRouter, WebSocket, Depends, Header, status

# ati code imports
from plugins.plugin_comms import ws_reader, ws_writer
import plugins.plugin_dependencies as pdpd

from .summon_models import SummonInfo, DBSession, AddEditSummonReq
from .summon_handler import SUMMON_HANDLER
from .summon_utils import add_edit_summon_info, close_summon_button_ws


router = APIRouter()
logger_name = "plugin_summon_button"
logger = logging.getLogger(logger_name)


def get_summon(x_api_key: str = Header(None)):
    if x_api_key is None:
        return None

    hashed_api_key = hashlib.sha256(x_api_key.encode("utf-8")).hexdigest()
    with DBSession() as dbsession:
        summon_info: SummonInfo = (
            dbsession.session.query(SummonInfo)
            .filter(SummonInfo.hashed_api_key == hashed_api_key)
            .one_or_none()
        )

        if summon_info:
            dbsession.session.expunge(summon_info)

    return summon_info


@router.get("/plugin/ws/api/v1/all_summon_info")
def get_all_summon_info(user_name=Depends(pdpd.get_user_from_header)):

    if not user_name:
        pdpd.raise_error("Unknown requester", 401)

    response = {}
    with DBSession() as dbsession:
        all_summons = dbsession.session.query(SummonInfo).all()
        if all_summons:
            for summon in all_summons:
                response.update(
                    {
                        summon.id: {
                            "hashed_api_key": summon.hashed_api_key,
                            "route": summon.route,
                        }
                    }
                )

    return response


@router.post("/plugin/ws/api/v1/add_edit_summon")
def add_edit_summon_button(
    add_edit_summon: AddEditSummonReq,
    user_name=Depends(pdpd.get_user_from_header),
):

    if not user_name:
        pdpd.raise_error("Unknown requester", 401)

    with DBSession() as dbsession:
        add_edit_summon_info(
            dbsession,
            id=add_edit_summon.id,
            api_key=add_edit_summon.api_key,
            route=add_edit_summon.route,
        )

    return {}


@router.get("/plugin/ws/api/v1/delete_summon/{id}")
def delete_summon(
    id: int,
    user_name=Depends(pdpd.get_user_from_header),
):
    if not user_name:
        pdpd.raise_error("Unknown requester", 401)

    with DBSession() as dbsession:
        summon_info = (
            dbsession.session.query(SummonInfo).filter(SummonInfo.id == id).one_or_none()
        )
        if not summon_info:
            pdpd.raise_error(f"Summon Button {summon_info} not found")

        dbsession.session.delete(summon_info)

        close_summon_button_ws(summon_info.id)

    return {}


@router.get("/plugin/ws/api/v1/plugin_summon_button")
async def check_connection():
    return {"uvicorn": "I Am Alive"}


@router.websocket("/plugin/ws/api/v1/summon_button")
async def summon_button_ws(websocket: WebSocket, summon_info=Depends(get_summon)):
    if not summon_info:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    await websocket.accept()

    summon_id = summon_info.id
    summon_handler = SUMMON_HANDLER()
    rw = [
        asyncio.create_task(ws_reader(websocket, "summon_button", summon_handler)),
        asyncio.create_task(
            ws_writer(websocket, "summon_button", format="json", unique_id=summon_id),
        ),
    ]
    try:
        await asyncio.gather(*rw)
    finally:
        [t.cancel() for t in rw]
