import sys
import time
import toml
import os
import utils.fleet_utils as fu
import logging
import logging.config
import redis
import json
from utils.upgrade_db import upgrade_db_schema
from models.db_session import DBSession

log_conf_path = os.path.join(os.getenv("FM_CONFIG_DIR"), "logging.conf")
logging.config.fileConfig(log_conf_path)
logger = logging.getLogger("confgure_fleet")


sys.path.append("/app/mule")
from mule.ati.common.config import load_mule_config


def regenerate_config():
    with open(os.getenv("ATI_CONSOLIDATED_CONFIG"), "w") as f:
        toml.dump(load_mule_config(os.getenv("ATI_CONFIG")), f)
    os.environ["ATI_CONFIG"] = os.environ["ATI_CONSOLIDATED_CONFIG"]


def main():
    # regenerate_mule_config for routing
    regenerate_config()
    config_path = os.environ["ATI_CONFIG"]
    logger.info(f"will use {config_path} as ATI_CONFIG")
    frontend_user_config = toml.load(
        os.path.join(os.getenv("FM_CONFIG_DIR"), "frontend_users.toml")
    )
    time.sleep(5)

    DB_UP = False
    while not DB_UP:
        try:
            fu.create_all_tables()
            upgrade_db_schema()
            DB_UP = True
        except Exception as e:
            logger.info(f"unable to create/clear data in db, \n Exception: {e}")

    logger.info(f"frontend user details in config {frontend_user_config}")

    with DBSession() as dbsession:
        for user_name, user_details in frontend_user_config["frontenduser"].items():
            role = user_details.get("role", "operator")
            fu.FrontendUserUtils.add_update_frontend_user(
                dbsession, user_name, user_details["hashed_password"], role
            )
        redis_conn = redis.from_url(os.getenv("FM_REDIS_URI"))
        all_sherpas = dbsession.get_all_sherpas()
        sherpa_names = []
        for sherpa in all_sherpas:
            sherpa_names.append(sherpa.name)
        redis_conn.set("all_sherpas", json.dumps(sherpa_names))


if __name__ == "__main__":
    main()
