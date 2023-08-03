from core.mongo_db import FMMongo 
from core.config_validator import ConfigValidator

fm_mongo = FMMongo()
fc_db = fm_mongo.get_database("fm_config")
fm_mongo.create_collection("optimal_dispatch", fc_db)
fm_mongo.add_validator("optimal_dispatch", fc_db, ConfigValidator.optimal_dispatch)


c = fm_mongo.get_collection("optimal_dispatch", fc_db)


new_config = {
    "method": "hungarian1",
    "prioritise_waiting_stations": True, 
    "eta_power_factor": 0.1,
    "priority_power_factor": 1.7,
    "max_trips_to_consider": 10,
    "permission_level": 3,
}

c.insert_one(new_config)
