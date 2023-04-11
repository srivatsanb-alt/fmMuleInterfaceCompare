import time
import logging
import os
import datetime
from sqlalchemy.orm.attributes import flag_modified

# ati code imports
import models.trip_models as tm
import master_fm_comms.mfm_utils as mu
import utils.trip_utils as tu
import utils.util as utils_util
from models.db_session import DBSession


def upload_map_files(mfm_context: mu.MFMContext):
    map_files_uploaded = [False]
    while not all(map_files_uploaded):
        with DBSession() as dbsession:
            all_fleets = dbsession.get_all_fleets()
            map_files_uploaded = [False] * len(all_fleets)
            i = 0
            for fleet in all_fleets:
                map_path = os.path.join(os.environ["FM_MAP_DIR"], f"{fleet.name}/map/")
                all_map_files = os.listdir(map_path)
                files = []
                for file_name in all_map_files:
                    files.append(
                        ("uploaded_files", open(os.path.join(map_path, file_name), "rb"))
                    )

                endpoint = "upload_map_files"
                response_status_code, response_json = mu.send_http_req_to_mfm(
                    mfm_context,
                    endpoint,
                    "post",
                    req_json=None,
                    files=files,
                    query=fleet.name,
                )

                if response_status_code == 200:
                    logging.getLogger("mfm_updates").info(
                        f"uploaded map files of {fleet.name} to master fm successfully"
                    )
                    map_files_uploaded[i] = True
                else:
                    logging.getLogger("mfm_updates").info(
                        f"unable to upload map_files to master fm, status_code {response_status_code}"
                    )
                    time.sleep(10)
                i += 1


def update_fleet_info(mfm_context: mu.MFMContext):
    fleet_info_sent = False
    while not fleet_info_sent:
        with DBSession() as dbsession:
            fleet_names = []
            master_fleet_info = []
            all_fleets = dbsession.get_all_fleets()
            for fleet in all_fleets:
                fleet_names.append(fleet.name)
                fleet_info = {
                    "name": fleet.name,
                    "customer": fleet.customer,
                    "site": fleet.site,
                    "location": fleet.location,
                }
                master_fleet_info.append(fleet_info)

            req_json = {
                "fleet_names": fleet_names,
                "master_fleet_info": master_fleet_info,
            }

            endpoint = "update_fleet_info"
            req_type = "post"

            response_status_code, response_json = mu.send_http_req_to_mfm(
                mfm_context, endpoint, req_type, req_json
            )

            if response_status_code == 200:
                logging.getLogger("mfm_updates").info(
                    f"sent fleet_info to mfm successfully, details: {req_json}"
                )
                fleet_info_sent = True
            else:
                logging.getLogger("mfm_updates").info(
                    f"unable to send fleet_info to mfm,  status_code {response_status_code}"
                )
                time.sleep(10)


def update_sherpa_info(mfm_context: mu.MFMContext):
    sherpa_info_sent = False
    while not sherpa_info_sent:
        with DBSession() as dbsession:
            sherpa_names = []
            master_sherpa_info = []
            all_sherpas = dbsession.get_all_sherpas()
            for sherpa in all_sherpas:
                sherpa_names.append(sherpa.name)
                sherpa_info = {
                    "name": sherpa.name,
                    "hwid": sherpa.hwid,
                    "fleet_name": sherpa.fleet.name,
                }
                master_sherpa_info.append(sherpa_info)

            req_json = {
                "sherpa_names": sherpa_names,
                "master_sherpa_info": master_sherpa_info,
            }

            endpoint = "update_sherpa_info"
            req_type = "post"

            response_status_code, response_json = mu.send_http_req_to_mfm(
                mfm_context, endpoint, req_type, req_json
            )

            if response_status_code == 200:
                logging.getLogger("mfm_updates").info(
                    f"sent sherpa_info to mfm successfully, details: {req_json}"
                )
                sherpa_info_sent = True
            else:
                logging.getLogger("mfm_updates").info(
                    f"unable to send sherpa_info to mfm,  status_code {response_status_code}"
                )
                time.sleep(10)


def update_trip_info(
    mfm_context: mu.MFMContext,
    dbsession: DBSession,
    last_trip_update_dt: str,
):
    success = False
    if last_trip_update_dt is None:
        last_trip_update_dt = datetime.datetime.now()
    else:
        last_trip_update_dt = utils_util.str_to_dt(last_trip_update_dt)

    new_trips = (
        dbsession.session.query(tm.Trip)
        .filter(tm.Trip.updated_at > last_trip_update_dt)
        .filter(tm.Trip.status.in_(tm.COMPLETED_TRIP_STATUS))
        .all()
    )

    if len(new_trips) == 0:
        logging.getLogger("mfm_updates").info(f"no new trip updates to be sent")
        return success

    trips_info = []
    for trip in new_trips:
        trips_info.append(tu.get_trip_status(trip))

    logging.getLogger("mfm_updates").info(f"new trips: {trips_info}")

    req_json = {"trips_info": trips_info}

    endpoint = "update_trip_info"
    req_type = "post"

    response_status_code, response_json = mu.send_http_req_to_mfm(
        mfm_context, endpoint, req_type, req_json
    )

    if response_status_code == 200:
        logging.getLogger("mfm_updates").info(
            f"sent trip_info to mfm successfully, details: {req_json}"
        )
        success = True

    else:
        logging.getLogger("mfm_updates").info(
            f"unable to send trip_info to mfm,  status_code {response_status_code}"
        )
    return success


def update_trip_analytics(
    mfm_context: mu.MFMContext,
    dbsession: DBSession,
    last_trip_analytics_update_dt: str,
):

    success = False
    if last_trip_analytics_update_dt is None:
        last_trip_analytics_update_dt = datetime.datetime.now()
    else:
        last_trip_analytics_update_dt = utils_util.str_to_dt(last_trip_analytics_update_dt)

    new_trip_analytics = (
        dbsession.session.query(tm.TripAnalytics)
        .filter(tm.TripAnalytics.updated_at > last_trip_analytics_update_dt)
        .filter(tm.TripAnalytics.end_time is not None)
        .all()
    )

    trips_analytics = []
    for trip_analytics in new_trip_analytics:
        trip: tm.Trip = dbsession.get_trip(trip_analytics.trip_id)
        if trip.status in tm.COMPLETED_TRIP_STATUS:
            trips_analytics.append(tu.get_trip_analytics(trip_analytics))

    if len(trips_analytics) == 0:
        logging.getLogger("mfm_updates").info("no new trip analytics to be updated")
        return success

    logging.getLogger("mfm_updates").info(f"new trip analytics: {trips_analytics}")

    req_json = {"trips_analytics": trips_analytics}

    endpoint = "update_trip_analytics"
    req_type = "post"

    response_status_code, response_json = mu.send_http_req_to_mfm(
        mfm_context, endpoint, req_type, req_json
    )

    if response_status_code == 200:
        logging.getLogger("mfm_updates").info(
            f"sent trip_analytics to mfm successfully, details: {req_json}"
        )
        success = True
    else:
        logging.getLogger("mfm_updates").info(
            f"unable to send trip_analytics to mfm,  status_code {response_status_code}"
        )

    return success


def update_fm_version_info(mfm_context: mu.MFMContext):
    fm_version_info_sent = False
    while not fm_version_info_sent:
        with DBSession() as dbsession:
            software_compatability = dbsession.get_compatability_info()
            compatible_sherpa_versions = software_compatability.info.get(
                "sherpa_versions", []
            )

            req_json = {
                "fm_tag": os.getenv("FM_TAG"),
                "compatible_sherpa_tags": compatible_sherpa_versions,
            }

            endpoint = "update_fm_version_info"
            req_type = "post"

            response_status_code, response_json = mu.send_http_req_to_mfm(
                mfm_context, endpoint, req_type, req_json
            )

            if response_status_code == 200:
                logging.getLogger("mfm_updates").info(
                    f"sent fm_version_info to mfm successfully, details: {req_json}"
                )
                fm_version_info_sent = True
            else:
                logging.getLogger("mfm_updates").info(
                    f"unable to send fm_version_info_sent to mfm,  status_code {response_status_code}"
                )
                time.sleep(10)


def send_mfm_updates():
    logging.getLogger().info("starting send_updates_to_mfm script")

    mfm_context: mu.MFMContext = mu.get_mfm_context()
    if mfm_context is None:
        return

    update_fm_version_info(mfm_context)
    update_fleet_info(mfm_context)
    upload_map_files(mfm_context)
    update_sherpa_info(mfm_context)

    while True:
        try:
            while True:
                with DBSession() as dbsession:
                    master_fm_data_upload_info = dbsession.get_master_data_upload_info()
                    any_updates_sent = False

                    # send trip update
                    last_trip_update_dt: str = master_fm_data_upload_info.info.get(
                        "last_trip_update_dt", None
                    )
                    last_trip_update_sent = update_trip_info(
                        mfm_context, dbsession, last_trip_update_dt
                    )
                    if last_trip_update_sent:
                        last_trip_update_dt = utils_util.dt_to_str(datetime.datetime.now())
                        any_updates_sent = True

                    # send trip analytics update
                    last_trip_analytics_update_dt: str = (
                        master_fm_data_upload_info.info.get(
                            "last_trip_analytics_update_dt", None
                        )
                    )
                    last_trip_analytics_sent = update_trip_analytics(
                        mfm_context, dbsession, last_trip_analytics_update_dt
                    )
                    if last_trip_analytics_sent:
                        last_trip_analytics_update_dt = utils_util.dt_to_str(
                            datetime.datetime.now()
                        )
                        any_updates_sent = True

                    # commit last update time to db
                    if any_updates_sent:
                        master_fm_data_upload_info.info.update(
                            {
                                "last_trip_analytics_update_dt": last_trip_analytics_update_dt,
                                "last_trip_update_dt": last_trip_update_dt,
                            }
                        )
                        flag_modified(master_fm_data_upload_info, "info")

                time.sleep(mfm_context.update_freq)

        except Exception as e:
            logging.getLogger("mfm_updates").info(
                f"exception in send_updates_to_mfm script {e}"
            )
