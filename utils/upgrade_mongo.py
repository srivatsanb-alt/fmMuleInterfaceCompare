import toml
import os

# ati code imports
from models.mongo_client import FMMongo
from models.db_session import DBSession

AVAILABLE_UPGRADES = ["4.0", "4.2", "4.21", "4.22", "4.3"]


def read_fm_config_toml_and_update_mongo_db(fm_mongo, fc_db):
    try:
        optimal_dispatch_col = fm_mongo.get_collection("optimal_dispatch", fc_db)
        optimal_dispatch_doc = fm_mongo.get_document_from_fm_config("optimal_dispatch")
        fleet_config = toml.load("/app/static/fleet_config/fleet_config.toml")
        optimal_dispatch_doc["max_trips_to_consider"] = fleet_config["optimal_dispatch"][
            "max_trips_to_consider"
        ]
        optimal_dispatch_col.find_one_and_replace({}, optimal_dispatch_doc)
        print("Successfully migrated data from fleet_config.toml")
    except Exception as e:
        print(f"unable to read fleet_config.toml and update mongo, exception: {e}")


def read_master_fm_toml_and_update_mongo_db(fm_mongo, fc_db):
    try:
        master_fm_collection = fm_mongo.get_collection("master_fm", fc_db)
        master_fm_doc = fm_mongo.get_document_from_fm_config("master_fm")
        master_fm_config = toml.load("/app/static/fleet_config/master_fm_config.toml")
        master_fm_doc["api_key"] = master_fm_config["master_fm"]["comms"]["api_key"]
        master_fm_doc["send_updates"] = master_fm_config["master_fm"]["comms"][
            "send_updates"
        ]
        master_fm_collection.find_one_and_replace({}, master_fm_doc)
        print("Successfully migrated data from master_fm_config.toml")
    except Exception as e:
        print(f"unable to read master_fm config.toml and update mongo, exception: {e}")


def read_conditional_trips_toml_and_update_mongo_db(fm_mongo, fc_db):
    try:
        conditional_trips_collection = fm_mongo.get_collection("conditional_trips", fc_db)
        conditional_trips_doc = fm_mongo.get_document_from_fm_config("conditional_trips")
        conditional_trips_config = toml.load(
            "/app/static/fleet_config/conditional_trips.toml"
        )

        conditional_trips_doc["auto_park"]["book"] = conditional_trips_config[
            "conditional_trips"
        ]["idling_sherpa"]["book"]
        conditional_trips_doc["auto_park"]["threshold"] = conditional_trips_config[
            "conditional_trips"
        ]["idling_sherpa"]["threshold"]
        conditional_trips_collection.find_one_and_replace({}, conditional_trips_doc)
        print("Successfully migrated data from conditional_trips.toml")
    except Exception as e:
        print(f"unable to read conditional_trips.toml and update mongo, exception: {e}")


class MongoUpgrade:
    def upgrade_to_4_0(self, fm_mongo):
        fc_db = fm_mongo.get_database("fm_config")
        read_master_fm_toml_and_update_mongo_db(fm_mongo, fc_db)
        read_conditional_trips_toml_and_update_mongo_db(fm_mongo, fc_db)
        read_fm_config_toml_and_update_mongo_db(fm_mongo, fc_db)

    def upgrade_to_4_2(self, fm_mongo):
        fc_db = fm_mongo.get_database("fm_config")
        mule_config_col = fm_mongo.get_collection("mule_config", fc_db)
        mule_config_doc = fm_mongo.get_document_from_fm_config("mule_config")
        redis_conf = {
            "port": int(os.getenv("REDIS_PORT")),
            "url": os.getenv("FM_REDIS_URI"),
        }
        mule_config_doc["mule_site_config"].update({"redis": redis_conf})
        mule_config_col.find_one_and_replace({}, mule_config_doc)
        print("Updated FM redis conf to mule_config")
    
    def upgrade_to_4_21(self, fm_mongo):
        fc_db = fm_mongo.get_database("fm_config")
        master_fm_col = fm_mongo.get_collection("master_fm", fc_db)
        master_fm_doc = fm_mongo.get_document_from_fm_config("master_fm")
        master_fm_doc.update({"recent_hours": 72})
        master_fm_col.find_one_and_replace({}, master_fm_doc)
        print("Updated recent hours in master_fm config")
    
    def upgrade_to_4_22(self, fm_mongo):
        fc_db = fm_mongo.get_database("fm_config")
        mule_config_col = fm_mongo.get_collection("mule_config", fc_db)
        mule_config_doc = fm_mongo.get_document_from_fm_config("mule_config")
        redis_conf = {
            "port": int(os.getenv("REDIS_PORT")),
            "url": os.getenv("FM_REDIS_URI"),
        }
        mule_config_doc["mule_site_config"].update({"redis": redis_conf})
        mule_config_col.find_one_and_replace({}, mule_config_doc)
        print("Updated FM redis conf to mule_config")

    def upgrade_to_4_3(self, fm_mongo):
        with DBSession() as db_session:
            fleet_names = db_session.get_all_fleet_names()
        fu_db = fm_mongo.get_database("frontend_users")
        user_details_col = fm_mongo.get_collection("user_details", fu_db)
          
        result = user_details_col.update_many(
            {},  
            { "$set": { "fleet_names": fleet_names } } 
        )
        print(f"Modified {result.modified_count} documents to add `fleet_names` field.")

    

def upgrade_mongo_schema():
    sorted_upgrades = sorted(AVAILABLE_UPGRADES, key=float)
    mongo_upgrade = MongoUpgrade()

    with FMMongo() as fm_mongo:
        db = fm_mongo.get_database("fm_config")
        fm_version_col = fm_mongo.get_collection("fm_version", db)
        fm_version_doc = fm_mongo.get_document_from_fm_config("fm_version")
        current_version = fm_version_doc["version"]
        for version in sorted_upgrades:
            if float(current_version) < float(version):
                print(f"Will try to upgrade mongo from v_{current_version} to v_{version}")
                version_txt = version.replace(".", "_")
                upgrade_fn = getattr(mongo_upgrade, f"upgrade_to_{version_txt}", None)
                if upgrade_fn is None:
                    print(
                        f"Invalid upgrade call, cannot upgrade from {current_version} to {version}"
                    )
                    continue

                upgrade_fn(fm_mongo)
                fm_version_doc["version"] = float(version)
                fm_version_col.find_one_and_replace({}, fm_version_doc)
                print(f"Successfully upgraded mongo_db from {current_version} to {version}")
