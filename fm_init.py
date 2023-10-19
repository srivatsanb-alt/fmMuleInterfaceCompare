import sys
import time
import toml
import os
import logging
import logging.config
import redis
import json

# ati code imports
import utils.log_utils as lu
import utils.db_utils as dbu
import utils.fleet_utils as fu
import models.misc_models as mm
from models.mongo_client import FMMongo
from utils.upgrade_db import upgrade_db_schema, maybe_drop_tables
from utils.upgrade_mongo import upgrade_mongo_schema

from models.db_session import DBSession

# get log config
logging.config.dictConfig(lu.get_log_config_dict())

sys.path.append("/app/mule")
from mule.ati.common.config import load_mule_config


def regenerate_mule_config():
    with open(os.getenv("ATI_CONFIG"), "w") as ac:
        with FMMongo() as fm_mongo:
            mule_config = fm_mongo.get_document_from_fm_config("mule_config")
        toml.dump(mule_config["mule_site_config"], ac)

    with open(os.getenv("ATI_CONSOLIDATED_CONFIG"), "w") as acc:
        toml.dump(load_mule_config(os.getenv("ATI_CONFIG")), acc)

    os.environ["ATI_CONFIG"] = os.environ["ATI_CONSOLIDATED_CONFIG"]

    config_path = os.environ["ATI_CONSOLIDATED_CONFIG"]
    logging.getLogger().info(f"Regenerated mule config, saved to: {config_path}")


def populate_redis_with_basic_info(dbsession: DBSession):
    redis_conn = redis.from_url(os.getenv("FM_REDIS_URI"))
    all_sherpas = dbsession.get_all_sherpas()
    sherpa_names = []
    for sherpa in all_sherpas:
        sherpa_names.append(sherpa.name)
    redis_conn.set("all_sherpas", json.dumps(sherpa_names))

    all_fleet_names = dbsession.get_all_fleet_names()
    redis_conn.set("all_fleet_names", json.dumps(all_fleet_names))

    # set seperate loggers for all sherpas
    lu.set_log_config_dict(sherpa_names)

    # redis_expire_timeout
    with FMMongo() as fm_mongo:
        rq_params = fm_mongo.get_document_from_fm_config("rq")

    # store default job timeout
    default_job_timeout = rq_params["default_job_timeout"]
    generic_handler_job_timeout = rq_params["generic_handler_job_timeout"]

    redis_conn.set("default_job_timeout_ms", default_job_timeout * 1000)
    redis_conn.set("generic_handler_job_timeout_ms", generic_handler_job_timeout * 1000)


def check_if_run_host_service_is_setup(dbsession):
    if not os.path.exists("/app/static/run_on_host_fifo") or not os.path.exists(
        "/app/static/run_on_host_updater_fifo"
    ):
        run_on_host_fifo_log = "Please setup run on host service by following the support manual available in downloads section"
        dbsession.add_notification(
            dbsession.get_customer_names(),
            run_on_host_fifo_log,
            mm.NotificationLevels.alert,
            mm.NotificationModules.generic,
        )


def main():
    time.sleep(5)

    DB_UP = False
    while not DB_UP:
        try:
            maybe_drop_tables()
            dbu.create_all_tables()
            upgrade_db_schema()
            DB_UP = True
        except Exception as e:
            logging.getLogger().info(
                f"unable to create/clear data in db, \n Exception: {e}"
            )
            time.sleep(5)

    with FMMongo() as fm_mongo:
        dbu.setfm_mongo_config(fm_mongo)

    upgrade_mongo_schema()

    # regenerate_mule_config for routing
    regenerate_mule_config()

    with DBSession() as dbsession:
        fu.add_software_compatability(dbsession)
        fu.add_master_fm_data_upload(dbsession)
        fu.add_sherpa_metadata(dbsession)

        # populate redis with basic info
        populate_redis_with_basic_info(dbsession)

        check_if_run_host_service_is_setup(dbsession)

    FM_TAG = os.getenv("FM_TAG")
    print(f"fm software tag: {FM_TAG}")


if __name__ == "__main__":
    main()
