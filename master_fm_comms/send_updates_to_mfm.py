import time
import logging
import os
import datetime
import redis
import json
from sqlalchemy import or_, func

# ati code imports
import models.trip_models as tm
import models.misc_models as mm
import master_fm_comms.mfm_utils as mu
import utils.trip_utils as tu
import utils.util as utils_util
import utils.fleet_utils as fu
from models.db_session import DBSession


def str_to_dt(dt_str, tdelta_h=None):
    result = datetime.datetime.now()
    if dt_str is None:
        if tdelta_h:
            result = result + datetime.timedelta(hours=tdelta_h)
    else:
        result = utils_util.str_to_dt(dt_str)

    return result


class SendEventUpdates2MFM:
    def __init__(self, redis_conn):
        self.redis_conn = redis_conn
        self.mfm_context: mu.MFMContext = mu.get_mfm_context()
        self.mfm_upload_dt_info = None
        self.any_updates_sent = False
        self.recent_hours = 24
        self.recent_dt = None
        self.last_conf_sent_unix_dt = time.time()

    def maybe_send_conf_to_mfm(self):
        temp = self.redis_conn.get("send_conf_to_mfm_unix_dt")
        if temp is None:
            return

        temp = float(temp.decode())
        if temp > self.last_conf_sent_unix_dt:
            logging.getLogger("mfm_updates").info(
                "Will send all fleet configuration to master fm again"
            )
            send_conf_to_mfm(self.mfm_context)
            self.last_conf_sent_unix_dt = time.time()

    def update_db(self, dbsession: DBSession):
        dbsession.session.commit()

    def initialize_master_data_upload_info(self, dbsession: DBSession):
        mfm_upload_dt_info = mm.MasterFMDataUploadts()
        dbsession.add_to_session(mfm_upload_dt_info)
        self.update_db(dbsession)

    def get_master_data_upload_info(self, dbsession: DBSession):
        self.mfm_upload_dt_info = dbsession.get_master_data_upload_info()

        if self.mfm_upload_dt_info is None:
            self.initialize_master_data_upload_info(dbsession)
            self.mfm_upload_dt_info = dbsession.get_master_data_upload_info()

        self.recent_dt = datetime.datetime.now() + datetime.timedelta(
            hours=-self.recent_hours
        )

    def update_file_upload_dt(self, file_upload: mm.FileUploads):
        last_file_upload_dt = file_upload.created_at
        if file_upload.updated_at:
            last_file_upload_dt = file_upload.updated_at
        self.mfm_upload_dt_info.last_file_upload_dt = last_file_upload_dt


def send_conf_to_mfm(mfm_context):
    update_fm_version_info(mfm_context)
    update_fleet_info(mfm_context)
    upload_map_files(mfm_context)
    update_sherpa_info(mfm_context)


def delete_map_file(mfm_context, fleet_name: str, file_name: str):
    del_req = {"fleet_name": fleet_name, "filename": file_name}
    response_status_code, response_json = mu.send_http_req_to_mfm(
        mfm_context, "delete_map_file", "post", req_json=del_req
    )
    if response_status_code != 200:
        logging.getLogger("mfm_updates").warning(
            f"Unable to delete map file {file_name} for fleet_name: {fleet_name}"
        )
        return False

    logging.getLogger("mfm_updates").info(
        f"Deleted map file {file_name} of the fleet: {fleet_name} successfully"
    )

    return True


def get_info_map_file(mfm_context: mu.MFMContext, fleet_name):
    endpoint = "get_map_file_info"
    response_status_code, response_json = mu.send_http_req_to_mfm(
        mfm_context, endpoint, "get", query=fleet_name
    )
    if response_status_code != 200:
        logging.getLogger("mfm_updates").warning(
            f"Unable to get map_file info of {fleet_name}"
        )
        return False, response_json
    logging.getLogger("mfm_updates").info(f"Got map_file info of {fleet_name} successfully")

    return True, response_json


def get_files_to_upload_delete(mfm_context: mu.MFMContext, fleet_name: str):
    status = False
    while not status:
        status, map_files_info = get_info_map_file(mfm_context, fleet_name)
        time.sleep(10)
    map_path = os.path.join(os.environ["FM_STATIC_DIR"], f"{fleet_name}/map/")
    all_map_files = [
        f for f in os.listdir(map_path) if os.path.isfile(os.path.join(map_path, f))
    ]
    files_to_upload = []

    files_to_del = [
        filename for filename in map_files_info.keys() if filename not in all_map_files
    ]

    for filename in all_map_files:
        filename_fq = os.path.join(map_path, filename)
        if map_files_info.get(filename) != fu.compute_sha1_hash(filename_fq):
            files_to_upload.append(filename_fq)
        else:
            logging.getLogger("mfm_updates").info(
                f"Already uploaded map_file {filename} of {fleet_name} to master fm"
            )

    return files_to_upload, files_to_del


def upload_map_files_fleet(mfm_context: mu.MFMContext, fleet_name: str):
    files_to_upload, files_to_del = get_files_to_upload_delete(mfm_context, fleet_name)
    upload_done = []
    ignored_large_files = []

    for filename in files_to_del:
        delete_success = False
        while not delete_success:
            delete_success = delete_map_file(mfm_context, fleet_name, filename)

    for filename_fq in files_to_upload:
        files = []
        files.append(("uploaded_files", open(filename_fq, "rb")))
        endpoint = "upload_map_file"
        response_status_code, response_json = mu.send_http_req_to_mfm(
            mfm_context,
            endpoint,
            "post",
            req_json=None,
            files=files,
            params=None,
            query=fleet_name,
        )
        if response_status_code == 200:
            logging.getLogger("mfm_updates").info(
                f"uploaded map file {filename_fq} of {fleet_name} to master fm successfully"
            )
            upload_done.append(filename_fq)

        elif response_status_code == 413:
            logging.getLogger("mfm_updates").warning(
                f"Ignoring to upload map file {filename_fq} of {fleet_name}, file size too large"
            )
            ignored_large_files.append(filename_fq)

        else:
            logging.getLogger("mfm_updates").info(
                f"unable to upload map_file {filename_fq} of {fleet_name} to master fm, status_code {response_status_code}"
            )
            time.sleep(5)

    return len(upload_done) + len(ignored_large_files) == len(files_to_upload)


def upload_map_files(mfm_context: mu.MFMContext):
    map_files_uploaded = [False]
    all_fleet_names = []
    with DBSession() as dbsession:
        all_fleet_names = dbsession.get_all_fleet_names()

    map_files_uploaded = [False] * len(all_fleet_names)
    while not all(map_files_uploaded):
        i = 0
        for fleet_name in all_fleet_names:
            if map_files_uploaded[i] is False:
                map_files_uploaded[i] = upload_map_files_fleet(mfm_context, fleet_name)
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
    event_updater: SendEventUpdates2MFM,
    dbsession: DBSession,
):

    new_trips = (
        dbsession.session.query(tm.Trip)
        .filter(tm.Trip.end_time > event_updater.mfm_upload_dt_info.last_trip_update_dt)
        .filter(tm.Trip.end_time > event_updater.recent_dt)
        .filter(tm.Trip.status.in_(tm.COMPLETED_TRIP_STATUS))
        .all()
    )

    if len(new_trips) == 0:
        logging.getLogger("mfm_updates").info("no new trip updates to be sent")
        return

    trips_info = []
    trip_ids = []
    for trip in new_trips:
        trip_info = tu.get_trip_status(trip)
        trip_ids.append(trip.id)
        del trip_info["trip_details"]["updated_at"]
        trips_info.append(trip_info)

    req_json = {"trips_info": trips_info}

    endpoint = "update_trip_info"
    req_type = "post"

    response_status_code, response_json = mu.send_http_req_to_mfm(
        event_updater.mfm_context, endpoint, req_type, req_json
    )

    if response_status_code == 200:
        logging.getLogger("mfm_updates").info(
            f"sent trip_info of trip_ids: {trip_ids} to mfm successfully"
        )
        event_updater.mfm_upload_dt_info.last_trip_update_dt = datetime.datetime.now()
        event_updater.update_db(dbsession)
    else:
        logging.getLogger("mfm_updates").info(
            f"unable to send trip_info to mfm,  status_code {response_status_code}"
        )


def update_trip_analytics(
    event_updater: SendEventUpdates2MFM,
    dbsession: DBSession,
):

    new_trip_analytics = (
        dbsession.session.query(tm.TripAnalytics)
        .join(tm.Trip, tm.Trip.id == tm.TripAnalytics.trip_id)
        .filter(
            tm.Trip.end_time
            > event_updater.mfm_upload_dt_info.last_trip_analytics_update_dt
        )
        .filter(tm.Trip.end_time > event_updater.recent_dt)
        .filter(tm.Trip.status.in_(tm.COMPLETED_TRIP_STATUS))
        .all()
    )

    trips_analytics = []
    trip_ids = []

    for trip_analytics in new_trip_analytics:
        ta = tu.get_trip_analytics(trip_analytics)
        del ta["updated_at"]
        del ta["created_at"]
        trips_analytics.append(ta)
        trip_ids.append(trip_analytics.trip_id)

    if len(trips_analytics) == 0:
        logging.getLogger("mfm_updates").info("no new trip analytics to be updated")
        return

    req_json = {"trips_analytics": trips_analytics}

    endpoint = "update_trip_analytics"
    req_type = "post"

    response_status_code, response_json = mu.send_http_req_to_mfm(
        event_updater.mfm_context, endpoint, req_type, req_json
    )

    if response_status_code == 200:
        logging.getLogger("mfm_updates").info(
            f"sent trip_analytics to mfm successfully, details: {req_json}"
        )
        event_updater.mfm_upload_dt_info.last_trip_analytics_update_dt = (
            datetime.datetime.now()
        )
        event_updater.update_db(dbsession)
    else:
        logging.getLogger("mfm_updates").info(
            f"unable to send trip_analytics to mfm,  status_code {response_status_code}"
        )


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
    event_updater: SendEventUpdates2MFM,
    dbsession: DBSession,
):

    fm_incidents = (
        dbsession.session.query(mm.FMIncidents)
        .filter(
            or_(
                mm.FMIncidents.created_at
                > event_updater.mfm_upload_dt_info.last_fm_incidents_update_dt,
                mm.FMIncidents.updated_at
                > event_updater.mfm_upload_dt_info.last_fm_incidents_update_dt,
            )
        )
        .all()
    )

    all_fm_incidents = []
    for fm_incident in fm_incidents:
        fm_incident_dict = utils_util.get_table_as_dict(mm.FMIncidents, fm_incident)
        del fm_incident_dict["id"]
        if fm_incident_dict.get("other_info"):

            """
            doing a json dumps since the other info has all data types,
            its becoming difficult to pydantic validation on server side
            """
            other_info_jdump = json.dumps(fm_incident_dict["other_info"])
            fm_incident_dict["other_info"] = {"json_dumped_other_info": other_info_jdump}

        all_fm_incidents.append(fm_incident_dict)

    if len(all_fm_incidents) == 0:
        logging.getLogger("mfm_updates").info("no new fm incidents to be updated")
        return

    req_json = {"all_fm_incidents": all_fm_incidents}

    endpoint = "update_fm_incidents"
    req_type = "post"

    response_status_code, response_json = mu.send_http_req_to_mfm(
        event_updater.mfm_context, endpoint, req_type, req_json
    )

    if response_status_code == 200:
        logging.getLogger("mfm_updates").info(
            f"sent fm_incidents to mfm successfully, details: {req_json}"
        )
        event_updater.mfm_upload_dt_info.last_fm_incidents_update_dt = (
            datetime.datetime.now()
        )
        event_updater.update_db(dbsession)
    else:
        logging.getLogger("mfm_updates").info(
            f"unable to send fm_incidents to mfm,  status_code {response_status_code}"
        )


def update_sherpa_oee(
    event_updater: SendEventUpdates2MFM,
    dbsession: DBSession,
):

    sherpa_oees = (
        dbsession.session.query(mm.SherpaOEE)
        .filter(
            func.date(mm.SherpaOEE.dt)
            >= func.date(event_updater.mfm_upload_dt_info.last_sherpa_oee_update_dt)
        )
        .all()
    )

    all_sherpa_oees = []
    for sherpa_oee in sherpa_oees:
        sherpa_oee_dict = utils_util.get_table_as_dict(mm.SherpaOEE, sherpa_oee)
        del sherpa_oee_dict["id"]
        all_sherpa_oees.append(sherpa_oee_dict)

    if len(all_sherpa_oees) == 0:
        logging.getLogger("mfm_updates").info("no new sherpa oee to be updated")
        return

    req_json = {"all_sherpa_oee": all_sherpa_oees}

    endpoint = "update_sherpa_oee"
    req_type = "post"

    response_status_code, response_json = mu.send_http_req_to_mfm(
        event_updater.mfm_context, endpoint, req_type, req_json
    )

    if response_status_code == 200:
        logging.getLogger("mfm_updates").info("sent sherpa oee to mfm successfully")
        event_updater.mfm_upload_dt_info.last_sherpa_oee_update_dt = datetime.datetime.now()
        event_updater.update_db(dbsession)
    else:
        logging.getLogger("mfm_updates").info(
            f"unable to send sherpa oee to mfm,  status_code: {response_status_code}"
        )


def upload_important_files(
    event_updater: SendEventUpdates2MFM,
    dbsession: DBSession,
):

    # upload files that are recent, sorted old->new
    file_uploads = (
        dbsession.session.query(mm.FileUploads)
        .filter(
            or_(
                func.date_trunc("seconds", mm.FileUploads.updated_at)
                > event_updater.mfm_upload_dt_info.last_file_upload_dt,
                func.date_trunc("seconds", mm.FileUploads.created_at)
                > event_updater.mfm_upload_dt_info.last_file_upload_dt,
            ),
        )
        .filter(
            or_(
                mm.FileUploads.created_at > event_updater.recent_dt,
                mm.FileUploads.updated_at > event_updater.recent_dt,
            )
        )
        .order_by(func.least(mm.FileUploads.updated_at, mm.FileUploads.created_at))
        .all()
    )

    endpoint = "upload_file"
    req_type = "post"

    # send one file at a time, update last_file_upload_dt
    for file_upload in file_uploads:
        params = {
            "filename": file_upload.filename,
            "uploaded_by": file_upload.uploaded_by,
            "type": file_upload.type,
            "fm_incident_id": file_upload.fm_incident_id,
        }

        file_to_upload = ("uploaded_file", open(file_upload.path, "rb"))
        response_status_code, response_json = mu.send_http_req_to_mfm(
            event_updater.mfm_context,
            endpoint,
            req_type,
            files=[file_to_upload],
            params=params,
        )
        if response_status_code == 200:
            logging.getLogger("mfm_updates").info(
                f"Successfully uploaded files with params: {params}"
            )
        elif response_status_code == 413:
            logging.getLogger("mfm_updates").info(
                f"Ignoring upload files with params: {params}, file size too large"
            )
        else:
            logging.getLogger("mfm_updates").info(
                f"unable to upload files with params {params}, status_code: {response_status_code}"
            )
            break

        event_updater.update_file_upload_dt(file_upload)
        event_updater.update_db(dbsession)


def send_mfm_updates():
    logging.getLogger().info("starting send_updates_to_mfm script")
    mfm_context: mu.MFMContext = mu.get_mfm_context()

    if mfm_context.send_updates is False:
        return

    send_mfm_updates_with_decorators(mfm_context)


@utils_util.proc_retry(sleep_time=30)
@utils_util.report_error
def send_mfm_updates_with_decorators(mfm_context):
    send_conf_to_mfm(mfm_context)
    with redis.from_url(os.getenv("FM_REDIS_URI")) as redis_conn:
        event_updater = SendEventUpdates2MFM(redis_conn)
        while True:
            with DBSession() as dbsession:
                event_updater.maybe_send_conf_to_mfm()
                event_updater.get_master_data_upload_info(dbsession)
                update_trip_info(event_updater, dbsession)
                update_trip_analytics(event_updater, dbsession)
                update_sherpa_oee(event_updater, dbsession)
                update_fm_incidents(event_updater, dbsession)
                upload_important_files(event_updater, dbsession)

            time.sleep(mfm_context.update_freq)
