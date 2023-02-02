import sys
import time
import toml
import os
import utils.fleet_utils as fu
import logging
import logging.config
from utils.upgrade_db import upgrade_db_schema

# setup logging
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

    fleet_config_path = os.path.join(os.getenv("FM_CONFIG_DIR"), "fleet_config.toml")
    config = toml.load(fleet_config_path)
    frontenduser = config["frontenduser"]
    time.sleep(5)

    DB_UP = False
    while not DB_UP:
        try:
            fu.create_all_tables()
            upgrade_db_schema()
            DB_UP = True
        except Exception as e:
            logger.info(f"unable to create/clear data in db, \n Exception: {e}")

    logger.info(f"frontend user details in config {frontenduser}")
    # for user_name, user_details in frontenduser.items():
    #    role = user_details.get("role", "operator")
    #
    #    fu.FrontendUserUtils.add_update_frontend_user(
    #        user_name, user_details["hashed_password"], role
    #    )


if __name__ == "__main__":
    main()
