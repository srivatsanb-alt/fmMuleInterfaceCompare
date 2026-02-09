from fastapi import Depends, APIRouter

from utils.rq_utils import Queues
import models.request_models as rqm
import app.routers.dependencies as dpd


router = APIRouter(
    prefix="/api/v1/superuser",
    tags=["superuser"],
    responses={404: {"description": "Not found"}},
)


@router.post(
    "/access/resource",
    response_model=rqm.ResourceResp,
)
async def super_user_resource_access(
    super_user_resource_req: rqm.SuperUserResourceReq,
    username= Depends(dpd.get_super_user)
):
    if username is None:
        dpd.raise_error("Unknown requester", 401)

    queue = Queues.queues_dict["resource_handler"]
    _response = await dpd.process_req_with_response(
        queue, super_user_resource_req, username
    )

    try:
        response = rqm.ResourceResp.from_json(_response)
    except:
        dpd.raise_error("Unable to obtain resource access response from RQ")

    return response
