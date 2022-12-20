import sys
import time
import toml
import os
from models.frontend_models import FrontendUser
from models.fleet_models import MapFile, AvailableSherpas, OptimalDispatchState
from models.visa_models import LinkedGates

sys.path.append("/app/mule")
import utils.fleet_utils as fu
from mule.ati.common.config import load_mule_config


def regenerate_config():
    with open(os.getenv("ATI_CONSOLIDATED_CONFIG"), "w") as f:
        toml.dump(load_mule_config(os.getenv("ATI_CONFIG")), f)
    os.environ["ATI_CONFIG"] = os.environ["ATI_CONSOLIDATED_CONFIG"]


fleet_config_path = os.path.join(os.getenv("FM_CONFIG_DIR"), "fleet_config.toml")
config = toml.load(fleet_config_path)
FLEET_CONFIG = config["fleet"]
fleet_names = FLEET_CONFIG["fleet_names"]
fleet_sherpas = config["fleet_sherpas"]
frontenduser = config["frontenduser"]
optimal_dispatch_config = config["optimal_dispatch"]


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
        DB_UP = True
    except Exception as e:
        print(f"unable to create/clear data in db, \n Exception: {e}")


print(f"frontend user details in config {frontenduser}")
for user_name, user_details in frontenduser.items():
    fu.add_frontend_user(user_name, user_details["hashed_password"])


# create fleet, update map details
for fleet_name in fleet_names:
    print(f"trying to update db tables for fleet : {fleet_name}")
    fu.maybe_update_map_files(fleet_name)
    fu.add_update_fleet(
        name=fleet_name,
        site=FLEET_CONFIG["site"],
        customer=FLEET_CONFIG["customer"],
        location=FLEET_CONFIG["location"],
    )
    fu.add_update_map(fleet_name)

# add sherpas to the db with info from config
for sherpa_name, sherpa_detail in fleet_sherpas.items():
    fu.add_update_sherpa(
        sherpa_name=sherpa_name,
        hwid=sherpa_detail["hwid"],
        api_key=sherpa_detail["api_key"],
        fleet_id=1,
    )
    fu.add_sherpa_to_fleet(sherpa=sherpa_name, fleet=sherpa_detail["fleet_name"])
    fu.add_update_sherpa_availability(sherpa_name, sherpa_detail["fleet_name"], False)
    print(f"added {sherpa_name}, {sherpa_detail} to db")

# regenerate_mule_config for routing
regenerate_config()
config_path = os.environ["ATI_CONFIG"]
print(f"will use {config_path} as ATI_CONFIG")
