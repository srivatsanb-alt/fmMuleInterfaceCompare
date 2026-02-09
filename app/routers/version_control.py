from fastapi import APIRouter, Depends
from sqlalchemy.orm.attributes import flag_modified

# ati code imports
from models.db_session import DBSession
import app.routers.dependencies as dpd
import core.common as ccm
from utils.auth_utils import AuthValidator


router = APIRouter(
    prefix="/api/v1/version_control",
    tags=["version_control"],
    responses={404: {"description": "Not found"}},
)


@router.get("/allow_new_sherpa_version/{version}")
async def allow_new_sherpa_version(
    version: str, user=Depends(AuthValidator('fm'))
):
    response = {}

    if not user:
        dpd.raise_error("Unknown requester", 401)

    with DBSession(engine=ccm.engine) as dbsession:
        software_compatability = dbsession.get_compatability_info()
        sherpa_versions = software_compatability.info.get("sherpa_versions", [])

        if version not in sherpa_versions:
            sherpa_versions.append(version)
            software_compatability.info.update({"sherpa_versions": sherpa_versions})
            flag_modified(software_compatability, "info")

    return response


@router.get("/disallow_sherpa_version/{version}")
async def disallow_sherpa_version(
    version: str, user=Depends(AuthValidator('fm'))
):
    response = {}

    if not user:
        dpd.raise_error("Unknown requester", 401)

    with DBSession(engine=ccm.engine) as dbsession:
        software_compatability = dbsession.get_compatability_info()
        sherpa_versions = software_compatability.info.get("sherpa_versions", [])
        if version in sherpa_versions:
            sherpa_versions.remove(version)
            software_compatability.info.update({"sherpa_versions": sherpa_versions})
            flag_modified(software_compatability, "info")
        else:
            dpd.raise_error(f"Sherpa version: {version} already not allowed")

    return response
