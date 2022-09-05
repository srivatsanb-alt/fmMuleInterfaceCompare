from app.routers.dependencies import get_db_session, get_user_from_header
from models.request_models import MasterDataInfo
from fastapi import APIRouter, Depends, HTTPException

router = APIRouter(
    responses={404: {"description": "Not found"}},
)


@router.get("/api/v1/info/fleet_names")
async def fleet_names(
    user_name=Depends(get_user_from_header), session=Depends(get_db_session)
):

    if not user_name:
        raise HTTPException(status_code=403, detail="Unknown requester")

    all_fleets = session.get_all_fleets()
    fleet_list = [fleet.name for fleet in all_fleets]

    return {"fleet_names": fleet_list}


@router.post("/api/v1/master_data/fleet")
async def master_data(
    master_data_info: MasterDataInfo,
    user_name=Depends(get_user_from_header),
    session=Depends(get_db_session),
):

    if not user_name:
        raise HTTPException(status_code=403, detail="Unknown requester")

    all_fleets = session.get_all_fleets()
    fleet_list = [fleet.name for fleet in all_fleets]

    if master_data_info.fleet_name not in fleet_list:
        raise HTTPException(status_code=403, detail="Unknown fleet")

    all_sherpas = session.get_all_sherpas()
    all_stations = session.get_all_stations()
    response = {}
    sherpa_list = []
    station_list = []

    if all_sherpas:
        sherpa_list = [
            sherpa.name
            for sherpa in all_sherpas
            if sherpa.fleet.name == master_data_info.fleet_name
        ]

    if all_stations:
        station_list = [
            station.name
            for station in all_stations
            if station.fleet.name == master_data_info.fleet_name
        ]

    response.update({"sherpa_list": sherpa_list})
    response.update({"station_list": station_list})

    sample_sherpa_status = {}
    all_sherpa_status = session.get_all_sherpa_status()
    sample_sherpa_status.update(
        {all_sherpa_status[0].sherpa_name: all_sherpa_status[0].__dict__}
    )
    sample_sherpa_status[all_sherpa_status[0].sherpa_name].update(
        all_sherpa_status[0].sherpa.__dict__
    )
    response.update({"sample_sherpa_status": sample_sherpa_status})

    sample_station_status = {}
    all_station_status = session.get_all_station_status()
    sample_station_status.update(
        {all_station_status[0].station_name: all_station_status[0].__dict__}
    )

    sample_station_status[all_station_status[0].station_name].update(
        all_station_status[0].station.__dict__
    )

    response.update({"sample_station_status": sample_station_status})

    # sample_trip_status = {}
    # data = None
    # try:
    #     data = session.query(Trip).first()
    #     sample_trip_status.update({data.id: data.__dict__})
    # except Exception as e:
    #     logging.get_logger().info(
    #             f"no trip data found, cannot send a sample_trip_status, {e}"
    #             )
    #
    # response.update({"sample_trip_status": sample_trip_status})

    return response
