from core.mongo_db import FMMongo
from core.config_validator import ConfigValidator, ConfigDefaults

fm_mongo = FMMongo()
fm_mongo.create_database("fm_config")
fc_db = fm_mongo.get_database("fm_config")

all_collection_names = ["optimal_dispatch", "comms", "backup", "stations", "master_fm", "conditional_trips"]

for collection_name in all_collection_names:
    fm_mongo.create_collection(collection_name, fc_db)
    fm_mongo.add_validator(collection_name, fc_db, getattr(ConfigValidator, collection_name))
    fc_db.command("collMod", collection_name, validator=getattr(ConfigValidator, collection_name))
    c = fm_mongo.get_collection(collection_name, fc_db)
    default_config = getattr(ConfigDefaults, collection_name)
    query = {}
    if c.find_one_and_replace(query, default_config):
         print(f"replaced {collection_name}")
    else:
        print("Unable to replace")
        c.insert_one(default_config)
        print(f"Inserted {collection_name}")
