import sys

sys.path.append("/app/mule")
from ati.common.config import load_mule_config
import toml
import os
import utils.fleet_utils as fu
import glob


def regenerate_config():
    with open(os.getenv("ATI_CONSOLIDATED_CONFIG"), "w") as f:
        toml.dump(load_mule_config(os.getenv("ATI_CONFIG")), f)
    os.environ["ATI_CONFIG"] = os.environ["ATI_CONSOLIDATED_CONFIG"]


# create all tables
fu.create_all_tables()

# create fleet, update map details
fleet_config = toml.load(os.path.join(os.getenv("FM_CONFIG_DIR"), "fleeet_config.toml"))["fleet"]
fleet_names = fleet_config["fleet_names"]
customer = fleet_config["customer"]
site = fleet_config["site"]
location = fleet_config["location"]
for fleet_name in fleet_names:
    try:
        print(f"trying to update db tables for fleet : {fleet_name}")
        fu.add_update_fleet(
            name=fleet_name, site=site, customer=customer, location=location
        )

        fu.add_update_map(fleet_name)
    except Exception as e:
        print(f"failed to update db tables for fleet {fleet_name}: {e}")


# add sherpas to the db with info from config
fleet_sherpas = toml.load(os.path.join(os.getenv("FM_CONFIG_DIR"), "fleet_config.toml"))[
    "fleet_sherpas"
]
for sherpa_name, sherpa_detail in fleet_sherpas.items():
    fu.add_sherpa(
        sherpa_name=sherpa_name,
        hwid=sherpa_detail["hwid"],
        api_key=sherpa_detail["api_key"],
        fleet_id=1,
    )
    fu.add_sherpa_to_fleet(sherpa=sherpa_name, fleet=sherpa_detail["fleet_name"])
    print(f"added {sherpa_name}, {sherpa_detail} to db")


# regenerate_mule_config for routing
regenerate_config()
config_path = os.environ["ATI_CONFIG"]
print(f"will use {config_path} as ATI_CONFIG")
