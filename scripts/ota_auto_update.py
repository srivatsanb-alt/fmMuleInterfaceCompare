import time
import logging
import os
import requests

# ati code imports
import app.routers.dependencies as dpd
import master_fm_comms.mfm_utils as mu
from models.mongo_client import FMMongo


def update_fm_to_fm_version(fm_version, access_token):
    kwargs = {"headers": {"X-USER-Token": access_token}}
    FM_PORT = os.getenv("FM_PORT")
    response = requests.get(
        f"http://127.0.0.1:{FM_PORT}/api/v1/ota_update/fm/update_to/{fm_version}", **kwargs
    )
    if response.status_code == 200:
        logging.getLogger("misc").info(f"Successfully updated to {fm_version}")
        return True

    return False


def auto_update_fm():
    mfm_context: mu.MFMContext = mu.get_mfm_context()
    if mfm_context.send_updates is False:
        return
    logging.getLogger("misc").info("Started auto update FM script")
    release_dt = None
    while True:
        with FMMongo() as fm_mongo:
            ota_update_fm_config = fm_mongo.get_document_from_fm_config("ota_update_fm")

        sleep_time = ota_update_fm_config["check_freq"]
        if ota_update_fm_config["auto_update"] is False:
            time.sleep(sleep_time)
            continue

        tag_to_fetch = ota_update_fm_config["tag_to_fetch"]
        temp = os.path.join(os.getenv("FM_STATIC_DIR"), f"release_{tag_to_fetch}.dt")

        if os.path.exists(temp) is True:
            with open(temp, "r") as temp_f:
            release_dt = temp_f.read()

        status_code, available_updates_json = mu.get_available_updates_fm(mfm_context)
        if status_code != 200:
            logging.getLogger("misc").warning("Unable to fetch info on available_updates")
            time.sleep(sleep_time)
            continue

        if tag_to_fetch in available_updates_json["available_updates"]:
            auth = mu.get_mfm_static_file_auth(mfm_context)
            release_notes, new_release_dt = mu.get_release_details(
                mfm_context, tag_to_fetch, auth
            )
            logging.info(f"current release_dt for {tag_to_fetch}: {release_dt}")
            logging.info(f"new release_dt for {tag_to_fetch}: {new_release_dt}")
            # if release_dt == new_release_dt:
            #     logging.getLogger("misc").info(
            #         f"No new updates to fetch, already on latest {tag_to_fetch}"
            #     )
            #     time.sleep(sleep_time)
            #     continue
            access_token = dpd.generate_jwt_token("ota_update_fm")
            if update_fm_to_fm_version(tag_to_fetch, access_token):
                temp = os.path.join(
                    os.getenv("FM_STATIC_DIR"), f"release_{tag_to_fetch}.dt"
                )
                with open(temp, "r") as temp_f:
                    temp_f.write(new_release_dt)

                logging.getLogger("misc").info(f"Requesting a restart all services")
                kwargs = {"headers": {"X-USER-Token": access_token}}
                FM_PORT = os.getenv("FM_PORT")
                response = requests.get(
                    f"http://127.0.0.1:{FM_PORT}/api/v1/scheduled_restart/{tag_to_fetch}/now"
                    ** kwargs,
                )
                if response.status_code == 200:
                    logging.getLogger("misc").info(
                        f"Successfully scheduled a restart all services"
                    )
                else:
                    logging.getLogger("misc").warning(
                        f"Unable scheduled a restart all services"
                    )

            time.sleep(sleep_time)
