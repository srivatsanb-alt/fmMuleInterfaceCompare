import sys
import time
import toml
import os
import utils.fleet_utils as fu
from models.frontend_models import FrontendUser
from models.fleet_models import MapFile, AvailableSherpas, OptimalDispatchState
from models.visa_models import LinkedGates


sys.path.append("/app/mule")
from ati.common.config import load_mule_config


def regenerate_config():
    with open(os.getenv("ATI_CONSOLIDATED_CONFIG"), "w") as f:
        toml.dump(load_mule_config(os.getenv("ATI_CONFIG")), f)
    os.environ["ATI_CONFIG"] = os.environ["ATI_CONSOLIDATED_CONFIG"]


fleet_config_path = os.path.join(os.getenv("FM_CONFIG_DIR"), "fleet_config.toml")

config = toml.load(fleet_config_path)
FLEET_CONFIG = config["fleet"]
frontenduser = config["frontenduser"]
optimal_dispatch_config = config["optimal_dispatch"]


print(f"frontend user details in config {frontenduser}")

time.sleep(5)

# create all tables
DB_UP = False
while not DB_UP:
    try:
        fu.create_all_tables()
        print("created all the tables")
        # clear all the data that has no state information
        fu.delete_table_contents(MapFile)
        fu.delete_table_contents(FrontendUser)
        fu.delete_table_contents(LinkedGates)
        fu.delete_table_contents(AvailableSherpas)
        fu.delete_table_contents(OptimalDispatchState)

        for user_name, user_details in frontenduser.items():
            fu.add_frontend_user(user_name, user_details["hashed_password"])

        fleet_names = FLEET_CONFIG["fleet_names"]

        # create fleet, update map details
        for fleet_name in fleet_names:
            try:
                print(f"trying to update db tables for fleet : {fleet_name}")
                fu.add_update_fleet(
                    name=fleet_name,
                    site=FLEET_CONFIG["site"],
                    customer=FLEET_CONFIG["customer"],
                    location=FLEET_CONFIG["location"],
                )
                fu.add_update_map(fleet_name)

            except Exception as e:
                print(f"failed to update db tables for fleet {fleet_name}: {e}")

        # add sherpas to the db with info from config
        fleet_sherpas = toml.load(
            os.path.join(os.getenv("FM_CONFIG_DIR"), "fleet_config.toml")
        )["fleet_sherpas"]
        for sherpa_name, sherpa_detail in fleet_sherpas.items():
            fu.add_update_sherpa(
                sherpa_name=sherpa_name,
                hwid=sherpa_detail["hwid"],
                api_key=sherpa_detail["api_key"],
                fleet_id=1,
            )
            fu.add_sherpa_to_fleet(sherpa=sherpa_name, fleet=sherpa_detail["fleet_name"])
            fu.add_update_sherpa_availability(
                sherpa_name, sherpa_detail["fleet_name"], False
            )
            print(f"added {sherpa_name}, {sherpa_detail} to db")

        # regenerate_mule_config for routing
        regenerate_config()
        config_path = os.environ["ATI_CONFIG"]
        print(f"will use {config_path} as ATI_CONFIG")

        DB_UP = True

    except Exception as e:
        print(f"unable to populate data in db, \n Exception: {e}")
