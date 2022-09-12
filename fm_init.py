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


fu.create_all_tables()
fleet_config = toml.load(os.path.join(os.getenv("FM_CONFIG_DIR"), "config.toml"))["fleet"]
fleet_names = fleet_config["fleet_names"]
customer = fleet_config["customer"]
site = fleet_config["site"]
location = fleet_config["location"]
for fleet_name in fleet_names:
    try:
        print(f"trying to update db tables for fleet : {fleet_name}")
        fu.add_update_fleet(name=fleet_name,
                            site=site,
                            customer=customer,
                            location=location
                            )

        fu.add_map(fleet_name)
    except Exception as e:
        print(f"failed to update db tables for fleet {fleet_name}: {e}")


regenerate_config()
config_path = os.environ["ATI_CONFIG"]
print(f"will use {config_path} as ATI_CONFIG")
