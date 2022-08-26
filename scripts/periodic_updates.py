from utils.comms import send_status_update
import logging
from models.db_session import session
from models.fleet_models import (
    SherpaStatus,
    Sherpa,
    Fleet,
    Station,
    StationStatus
)
import time
import inspect


def get_table_as_dict(model, model_obj):
    cols = model.__table__.columns.keys()
    result = {}
    model_dict = model_obj.__dict__
    for col in cols:
        if col in ["created_at", "updated_at"]:
            pass
        elif inspect.isclass(model_dict[col]):
            pass
        else:
            if isinstance(model_dict[col], list):
                skip = False
                for item in model_dict[col]:
                    if inspect.isclass(item):
                        skip = True
                        break
                if skip:
                    continue
                    
            result.update({col: model_dict[col]})

    return result


def get_fleet_status_msg(fleet):
    msg = {}
    all_station_status = session.get_all_station_status()
    all_sherpa_status = session.get_all_sherpa_status()

    sherpa_status_update = {}
    station_status_update = {}

    if all_sherpa_status:
        for sherpa_status in all_sherpa_status:
            if sherpa_status.sherpa.fleet.name == fleet.name:
                sherpa_status_update.update({
                                            sherpa_status.sherpa_name:
                                            get_table_as_dict(SherpaStatus, sherpa_status)})

                sherpa_status_update[sherpa_status.sherpa_name].update(
                                            get_table_as_dict(Sherpa, sherpa_status.sherpa))

    if all_station_status:
        for station_status in all_station_status:
            if station_status.station.fleet.name == fleet.name:
                station_status_update.update({station_status.station_name:
                                              get_table_as_dict(StationStatus, station_status)})

                station_status_update[station_status.station_name].update(
                                        get_table_as_dict(Station, station_status.station))

    msg.update({"sherpa_status": sherpa_status_update})
    msg.update({"station_status": station_status_update})
    msg.update({"fleet_status": get_table_as_dict(Fleet, fleet)})
    msg.update({"fleet_name": fleet.name})
    msg.update({"type": "fleet_status"})

    return msg


def send_periodic_updates():
    logging.getLogger().info("starting periodic updates script")
    time.sleep(5)
    while True:
        all_fleets = session.get_all_fleets()
        for fleet in all_fleets:
            msg = get_fleet_status_msg(fleet)
            send_status_update(msg)

        time.sleep(1)
