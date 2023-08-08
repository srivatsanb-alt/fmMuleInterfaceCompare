import sys
import time
import toml
import os
import logging
import logging.config
import redis
import json
import inspect

# ati code imports
import utils.log_utils as lu
import utils.fleet_utils as fu
import utils.config_utils as cu
from models.mongo_client import FMMongo
from utils.upgrade_db import upgrade_db_schema, maybe_drop_tables
from models.db_session import DBSession

# get log config
logging.config.dictConfig(lu.get_log_config_dict())

sys.path.append("/app/mule")
from mule.ati.common.config import load_mule_config


def setfm_mongo_config():
    with FMMongo() as fm_mongo:
        fm_mongo.create_database("fm_config")
        fc_db = fm_mongo.get_database("fm_config")
        config_val_members = inspect.getmembers(cu.ConfigValidator)
        all_collection_names = []
        for val in config_val_members:
            if not val[0].startswith("__"):
                all_collection_names.append(val[0])

        for collection_name in all_collection_names:
            create_col_kwargs = getattr(cu.CreateColKwargs, collection_name, None)
            if create_col_kwargs is None:
                create_col_kwargs = getattr(cu.CreateColKwargs, "capped_default")

            fm_mongo.create_collection(collection_name, fc_db, **create_col_kwargs)
            fm_mongo.add_validator(
                collection_name, fc_db, getattr(cu.ConfigValidator, collection_name)
            )
            fc_db.command(
                "collMod",
                collection_name,
                validator=getattr(cu.ConfigValidator, collection_name),
            )
            c = fm_mongo.get_collection(collection_name, fc_db)
            default_config = getattr(cu.ConfigDefaults, collection_name)

            if create_col_kwargs["capped"]:
                c.insert_one(default_config)

            # else:
            #    query = {}
            #    c.find_one_and_replace(query, default_config)

            logging.getLogger().info(f"updated {collection_name}")


def regenerate_config():
    with open(os.getenv("ATI_CONSOLIDATED_CONFIG"), "w") as f:
        toml.dump(load_mule_config(os.getenv("ATI_CONFIG")), f)
    os.environ["ATI_CONFIG"] = os.environ["ATI_CONSOLIDATED_CONFIG"]


def update_frontend_user_details(dbsession: DBSession):

    fu.FrontendUserUtils.delete_all_frontend_users(dbsession)
    dbsession.session.flush()

    frontend_user_config = toml.load(
        os.path.join(os.getenv("FM_CONFIG_DIR"), "frontend_users.toml")
    )
    logging.getLogger().info(f"frontend user details in config {frontend_user_config}")

    for user_name, user_details in frontend_user_config["frontenduser"].items():
        role = user_details.get("role", "operator")
        fu.FrontendUserUtils.add_update_frontend_user(
            dbsession, user_name, user_details["hashed_password"], role
        )


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
    fleet_config = toml.load(os.path.join(os.getenv("FM_CONFIG_DIR"), "fleet_config.toml"))

    # store default job timeout
    default_job_timeout = fleet_config["fleet"]["rq"].get("default_job_timeout", 15)
    generic_handler_job_timeout = fleet_config["fleet"]["rq"].get(
        "generic_handler_job_timeout", 10
    )

    redis_conn.set("default_job_timeout_ms", default_job_timeout * 1000)
    redis_conn.set("generic_handler_job_timeout_ms", generic_handler_job_timeout * 1000)


def main():
    # regenerate_mule_config for routing
    regenerate_config()
    config_path = os.environ["ATI_CONFIG"]
    logging.getLogger().info(f"will use {config_path} as ATI_CONFIG")
    time.sleep(5)

    DB_UP = False
    while not DB_UP:
        try:
            maybe_drop_tables()
            fu.create_all_tables()
            upgrade_db_schema()
            DB_UP = True
        except Exception as e:
            logging.getLogger().info(
                f"unable to create/clear data in db, \n Exception: {e}"
            )
            time.sleep(5)

    setfm_mongo_config()

    with DBSession() as dbsession:
        fu.add_software_compatability(dbsession)
        fu.add_master_fm_data_upload(dbsession)
        fu.add_sherpa_metadata(dbsession)

        # update frontenduser details
        update_frontend_user_details(dbsession)

        # populate redis with basic info
        populate_redis_with_basic_info(dbsession)

    FM_TAG = os.getenv("FM_TAG")
    print(f"fm software tag: {FM_TAG}")


if __name__ == "__main__":
    main()
