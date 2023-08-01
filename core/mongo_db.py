import pymongo as pm
import os


def get_mongo_client(uri: str):
    mongo_client = pm.MongoClient(uri)
    return mongo_client


class FMMongo:
    def __init__(self, uri=None):
        if uri is None:
            uri = os.getenv("FM_MONGO_DATABASE_URI")
        self.mongo_client = get_mongo_client(uri)

    def list_database_names(self):
        return self.mongo_client.list_database_names()

    def get_database(self, db_name):
        return self.mongo_client[db_name]

    def get_collection(self, collection_name, db_name):
        return self.mongo_client[db_name][collection_name]
