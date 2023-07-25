import time
import logging
import os
import datetime
from sqlalchemy import or_, func
from sqlalchemy.orm.attributes import flag_modified

# ati code imports
import models.trip_models as tm
import models.misc_models as mm
import master_fm_comms.mfm_utils as mu
import utils.trip_utils as tu
import utils.util as utils_util
from models.db_session import DBSession


def send_reset_map_dir_req(mfm_context, fleet_name: str):
    response_status_code, response_json = mu.send_http_req_to_mfm(
        mfm_context,
        "reset_map_dir",
        "get",
        query=fleet_name,
    )
    if response_status_code != 200:
        logging.getLogger("mfm_updates").warning(
            f"Unable to reset map dir for fleet_name: {fleet_name}"
        )
        return False

    logging.getLogger("mfm_updates").info(
        f"Reset map dir of the fleet: {fleet_name} successfully"
    )

    return True


def upload_map_files(mfm_context: mu.MFMContext):
    map_files_uploaded = [False]
    while not all(map_files_uploaded):
        with DBSession() as dbsession:
            all_fleets = dbsession.get_all_fleets()
            map_files_uploaded = [False] * len(all_fleets)
            i = 0
            for fleet in all_fleets:
                map_path = os.path.join(os.environ["FM_STATIC_DIR"], f"{fleet.name}/map/")
                all_map_files = os.listdir(map_path)
                upload_done = []
                while not send_reset_map_dir_req(mfm_context, fleet.name):
                    time.sleep(30)
                for file_name in all_map_files:
                    files = []
                    files.append(
                        ("uploaded_files", open(os.path.join(map_path, file_name), "rb"))
                    )
                    endpoint = "upload_map_file"
                    response_status_code, response_json = mu.send_http_req_to_mfm(
                        mfm_context,
                        endpoint,
                        "post",
                        req_json=None,
                        files=files,
                        params=None,
                        query=fleet.name,
                    )
                    if response_status_code == 200:
                        logging.getLogger("mfm_updates").info(
                            f"uploaded map file {file_name} of {fleet.name} to master fm successfully"
                        )
                        upload_done.append(file_name)
                        if len(upload_done) == len(all_map_files):
                            map_files_uploaded[i] = True
                    else:
                        logging.getLogger("mfm_updates").info(
                            f"unable to upload map_file {file_name} of {fleet.name} to master fm, status_code {response_status_code}"
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

    recent_dt = datetime.datetime.now() + datetime.timedelta(hours=-24)

    new_trips = (
        dbsession.session.query(tm.Trip)
        .filter(tm.Trip.updated_at > last_trip_update_dt)
        .filter(tm.Trip.updated_at > recent_dt)
        .filter(tm.Trip.status.in_(tm.COMPLETED_TRIP_STATUS))
        .all()
    )

    if len(new_trips) == 0:
        logging.getLogger("mfm_updates").info(f"no new trip updates to be sent")
        return success

    trips_info = []
    for trip in new_trips:
        trip_info = tu.get_trip_status(trip)
        del trip_info["trip_details"]["updated_at"]
        trips_info.append(trip_info)

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

    recent_dt = datetime.datetime.now() + datetime.timedelta(hours=-24)

    new_trip_analytics = (
        dbsession.session.query(tm.TripAnalytics)
        .filter(tm.TripAnalytics.updated_at > last_trip_analytics_update_dt)
        .filter(tm.TripAnalytics.updated_at > recent_dt)
        .filter(tm.TripAnalytics.end_time is not None)
        .all()
    )

    trips_analytics = []
    for trip_analytics in new_trip_analytics:
        trip: tm.Trip = dbsession.get_trip(trip_analytics.trip_id)
        if trip.status in tm.COMPLETED_TRIP_STATUS:
            ta = tu.get_trip_analytics(trip_analytics)
            del ta["updated_at"]
            del ta["created_at"]
            trips_analytics.append(ta)

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


def update_fm_incidents(
    mfm_context: mu.MFMContext,
    dbsession: DBSession,
    last_fm_incidents_update_dt,
):
    success = False
    if last_fm_incidents_update_dt is None:
        last_fm_incidents_update_dt = datetime.datetime.now() + datetime.timedelta(
            hours=-24
        )
    else:
        last_fm_incidents_update_dt = utils_util.str_to_dt(last_fm_incidents_update_dt)

    fm_incidents = (
        dbsession.session.query(mm.FMIncidents)
        .filter(
            or_(
                mm.FMIncidents.created_at > last_fm_incidents_update_dt,
                mm.FMIncidents.updated_at > last_fm_incidents_update_dt,
            )
        )
        .all()
    )

    all_fm_incidents = []
    for fm_incident in fm_incidents:
        fm_incident_dict = utils_util.get_table_as_dict(mm.FMIncidents, fm_incident)
        del fm_incident_dict["id"]
        all_fm_incidents.append(fm_incident_dict)

    if len(all_fm_incidents) == 0:
        logging.getLogger("mfm_updates").info("no new fm incidents to be updated")
        return success

    req_json = {"all_fm_incidents": all_fm_incidents}

    endpoint = "update_fm_incidents"
    req_type = "post"

    response_status_code, response_json = mu.send_http_req_to_mfm(
        mfm_context, endpoint, req_type, req_json
    )

    if response_status_code == 200:
        logging.getLogger("mfm_updates").info(
            f"sent fm_incidents to mfm successfully, details: {req_json}"
        )
        success = True
    else:
        logging.getLogger("mfm_updates").info(
            f"unable to send fm_incidents to mfm,  status_code {response_status_code}"
        )
    return success


def update_sherpa_oee(
    mfm_context: mu.MFMContext,
    dbsession: DBSession,
    last_sherpa_oee_update_dt,
):

    recent_hours = -24
    success = False
    if last_sherpa_oee_update_dt is None:
        last_sherpa_oee_update_dt = datetime.datetime.now() + datetime.timedelta(
            hours=recent_hours
        )
    else:
        last_sherpa_oee_update_dt = utils_util.str_to_dt(last_sherpa_oee_update_dt)

    sherpa_oees = (
        dbsession.session.query(mm.SherpaOEE)
        .filter(func.date(mm.SherpaOEE.dt) >= func.date(last_sherpa_oee_update_dt))
        .all()
    )

    all_sherpa_oees = []
    for sherpa_oee in sherpa_oees:
        sherpa_oee_dict = utils_util.get_table_as_dict(mm.SherpaOEE, sherpa_oee)
        all_sherpa_oees.append(sherpa_oee_dict)

    if len(all_sherpa_oees) == 0:
        logging.getLogger("mfm_updates").info("no new sherpa oee to be updated")
        return success

    req_json = {"all_sherpa_oee": all_sherpa_oees}

    endpoint = "update_sherpa_oee"
    req_type = "post"

    response_status_code, response_json = mu.send_http_req_to_mfm(
        mfm_context, endpoint, req_type, req_json
    )

    if response_status_code == 200:
        logging.getLogger("mfm_updates").info(
            f"sent sherpa oee to mfm successfully, details: {req_json}"
        )
        success = True
    else:
        logging.getLogger("mfm_updates").info(
            f"unable to send sherpa oee to mfm,  status_code: {response_status_code}"
        )
    return success


def upload_important_files(
    mfm_context: mu.MFMContext, dbsession: DBSession, last_file_upload_dt
):

    recent_hours = -24
    success = False

    if last_file_upload_dt:
        temp_last_file_update_dt = utils_util.str_to_dt(last_file_upload_dt)
        temp_last_file_update_dt = max(
            temp_last_file_update_dt,
            (datetime.datetime.now() + datetime.timedelta(hours=recent_hours)),
        )
    else:
        temp_last_file_update_dt = datetime.datetime.now()

    recent_dt = temp_last_file_update_dt + datetime.timedelta(hours=recent_hours)

    # upload files that are recent
    file_uploads = (
        dbsession.session.query(mm.FileUploads)
        .filter(
            or_(
                func.date_trunc("seconds", mm.FileUploads.updated_at)
                > temp_last_file_update_dt,
                func.date_trunc("seconds", mm.FileUploads.created_at)
                > temp_last_file_update_dt,
            ),
        )
        .filter(
            or_(
                mm.FileUploads.created_at > recent_dt, mm.FileUploads.updated_at > recent_dt
            )
        )
        .order_by(func.least(mm.FileUploads.updated_at, mm.FileUploads.created_at))
        .all()
    )

    endpoint = "upload_file"
    req_type = "post"

    for file_upload in file_uploads:
        params = {
            "filename": file_upload.filename,
            "uploaded_by": file_upload.uploaded_by,
            "type": file_upload.type,
            "fm_incident_id": file_upload.fm_incident_id,
        }

        file_to_upload = ("uploaded_file", open(file_upload.path, "rb"))
        response_status_code, response_json = mu.send_http_req_to_mfm(
            mfm_context, endpoint, req_type, files=[file_to_upload], params=params
        )
        if response_status_code == 200:
            logging.getLogger("mfm_updates").info(
                f"Successfully uploaded files with params: {params}"
            )
            success = True
            temp_last_file_update_dt = file_upload.created_at
            if file_upload.updated_at:
                temp_last_file_update_dt = file_upload.updated_at
        else:
            logging.getLogger("mfm_updates").info(
                f"unable to upload files with params {params}, status_code: {response_status_code}"
            )
            break

    return success, temp_last_file_update_dt


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

                    # send sherpa oees
                    last_sherpa_oee_update_dt: str = master_fm_data_upload_info.info.get(
                        "last_sherpa_oee_update_dt", None
                    )
                    last_sherpa_oee_sent = update_sherpa_oee(
                        mfm_context, dbsession, last_sherpa_oee_update_dt
                    )
                    if last_sherpa_oee_sent:
                        last_sherpa_oee_update_dt = utils_util.dt_to_str(
                            datetime.datetime.now()
                        )
                        any_updates_sent = True

                    # send fm incidents
                    last_fm_incidents_update_dt: str = master_fm_data_upload_info.info.get(
                        "last_fm_incidents_update_dt", None
                    )
                    last_fm_incidents_sent = update_fm_incidents(
                        mfm_context, dbsession, last_fm_incidents_update_dt
                    )
                    if last_fm_incidents_sent:
                        last_fm_incidents_update_dt = utils_util.dt_to_str(
                            datetime.datetime.now()
                        )
                        any_updates_sent = True

                    # upload important files
                    last_file_upload_dt: str = master_fm_data_upload_info.info.get(
                        "last_file_upload_dt", None
                    )

                    (
                        last_file_uplaod_success,
                        temp_last_file_update_dt,
                    ) = upload_important_files(mfm_context, dbsession, last_file_upload_dt)

                    # need not set last_file_upload_dt
                    if last_file_uplaod_success:
                        any_updates_sent = True
                        last_file_upload_dt = utils_util.dt_to_str(temp_last_file_update_dt)

                    # commit last update time to db
                    if any_updates_sent:
                        master_fm_data_upload_info.info.update(
                            {
                                "last_trip_analytics_update_dt": last_trip_analytics_update_dt,
                                "last_trip_update_dt": last_trip_update_dt,
                                "last_sherpa_oee_update_dt": last_sherpa_oee_update_dt,
                                "last_fm_incidents_update_dt": last_fm_incidents_update_dt,
                                "last_file_upload_dt": last_file_upload_dt,
                            }
                        )
                        flag_modified(master_fm_data_upload_info, "info")

                time.sleep(mfm_context.update_freq)

        except Exception as e:
            logging.getLogger("mfm_updates").info(
                f"exception in send_updates_to_mfm script {e}"
            )
