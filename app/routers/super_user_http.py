from fastapi import Depends, APIRouter

from utils.rq_utils import Queues
import models.request_models as rqm
import app.routers.dependencies as dpd
from utils.auth_utils import AuthValidator


router = APIRouter(
    prefix="/api/v1/superuser",
    tags=["superuser"],
    responses={404: {"description": "Not found"}},
)

# TODO: super user was present in the mongodb users collection earlier.
# We need to either migrate that to the new auth system or remove this dependency.
@router.post(
    "/access/resource",
    response_model=rqm.ResourceResp,
)
async def super_user_resource_access(
    super_user_resource_req: rqm.SuperUserResourceReq,
    user= Depends(AuthValidator('fm')),
):
    if user is None:
        dpd.raise_error("Unknown requester", 401)
    
    username = user.get('user_name')

    queue = Queues.queues_dict["resource_handler"]
    _response = await dpd.process_req_with_response(
        queue, super_user_resource_req, username
    )

    try:
        response = rqm.ResourceResp.from_json(_response)
    except:
        dpd.raise_error("Unable to obtain resource access response from RQ")

    return response
