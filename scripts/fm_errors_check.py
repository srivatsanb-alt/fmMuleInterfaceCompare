import time
import logging
import re
import json

import os
import glob
from models.db_session import DBSession
from utils.util import report_error
import models.misc_models as mm

def add_fm_incident(dbsession, error_dict):
    fm_incident = mm.FMIncidents(
        type="fm_error",
        code=error_dict['code'],
        incident_id=error_dict['random_id'],
        module=error_dict['module'],
        message=error_dict['error_msg'] ,
        data_path=error_dict['file_path'],
        data_uploaded= True,
        )
    dbsession.add_to_session(fm_incident)
    logging.getLogger().info(f"fm_incident uploaded")

def add_fm_error_file_upload(dbsession, error_dict):
    file_upload = mm.FileUploads(
        filename=error_dict['filename'],
        path=error_dict['file_path'],
        type="fm_error",
        fm_incident_id=error_dict['random_id'],
        uploaded_by="self",
    )
    dbsession.add_to_session(file_upload)
    logging.getLogger().info(f"file uploaded")


@report_error
def periodic_error_check():
    logging.getLogger().info(f"started periodic_error_check script")

    while True:
        with DBSession() as dbsession:
            fm_error_dir = os.path.join(os.getenv("FM_STATIC_DIR"), "fm_errors")
            files = glob.glob(fm_error_dir + "/*")
            files.sort(key=os.path.getctime, reverse=True)
            now = time.time()
            for file_path in files:
                two_minutes_ago = now - 120
                if os.path.getctime(file_path) < two_minutes_ago:
                    break
                filename = os.path.basename(file_path)

                # file_path = os.path.join(fm_error_dir, filename)
                file_upload = dbsession.get_file_upload(filename)

                if file_upload:
                    logging.getLogger().info(f"File is already present")
                    continue

                pattern = r"_([A-Z0-9]+)\.log"
                match = re.search(pattern, file_path)
                with open(file_path, "r") as f:
                    error_dict=json.load(f)
                error_dict['file_path']=file_path
                error_dict['filename']=filename
                if match is not None:
                    random_id = match.group(1)
                    error_dict['incident_id']=random_id
                    add_fm_incident(dbsession, error_dict)
                    add_fm_error_file_upload(dbsession, error_dict)
       
        time.sleep(120)
