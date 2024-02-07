# ati code imports
from models.mongo_client import FMMongo
from utils.db_utils import maybe_add_psql_db_config


def get_max_psql_connections_from_mongo():
    with FMMongo() as fm_mongo:
        psql_db_config = fm_mongo.get_database("psql_db_config")
        c = fm_mongo.get_collection("connection_settings", psql_db_config)
        connection_settings_doc = c.find_one({})
        max_connections = connection_settings_doc["max_connections"]
        print(max_connections)
    return max_connections


def create_psql_db_config():
    with FMMongo() as fm_mongo:
        maybe_add_psql_db_config(fm_mongo)
