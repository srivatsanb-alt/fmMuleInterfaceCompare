from core.mongo_db import FMMongo
from core.config_validator import ConfigValidator, ConfigDefaults

fm_mongo = FMMongo()
fc_db = fm_mongo.get_database("fm_config")

all_collection_names = ["optimal_dispatch", "comms", "backup", "simulator"]

for collection_name in all_collection_names:
    fm_mongo.create_collection(collection_name, fc_db)
    fm_mongo.add_validator(collection_name, fc_db, getattr(ConfigValidator, collection_name))
    c = fm_mongo.get_collection(collection_name, fc_db)
    try:
        c.find_one_and_replace({}, getattr(ConfigDefaults, collection_name))
        print(f"replaced {collection_name}")
    except Exception as e:
        print("Unable to replace")
        c.insert_one(getattr(ConfigDefaults, collection_name))
        print(f"Inserted {collection_name}")
