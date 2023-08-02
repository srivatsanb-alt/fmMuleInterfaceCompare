import pymongo as pm
import os


def get_mongo_client(uri: str):
    mongo_client = pm.MongoClient(uri)
    return mongo_client


class PERMISSION_LEVELS:
    OPERATOR = 0
    SUPPORT = 1
    DEV = 2


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

    def create_index(collection, var, is_unique=True):
        collection.create_index(var, unique=is_unique)

    def add_permission_level(self, level, **kwargs):
        level_int = getattr(PERMISSION_LEVELS, level.upper(), None)
        if level_int is None:
            raise Exception("Invalid permission level")
        kwargs.update({"permission_level": level_int})

    def get_all_collection_names(self, db_name):
        return self.mongo_client[db_name].list_collection_names()

    def get_all_documents(self, collection):
        return collection.find()

    def get_documents_with_filter(self, collection, filter):
        return collection.find(filter)

    def get_documents_with_permission_level(self, collection, level):
        filter = {"permission_level": {"$lt": level}}
        return self.get_documents_with_filter(collection, filter)

    def get_all_document_types(collection):
        all_types = []
        cursor = collection.find({}, {"type": 1})
        for record in cursor:
            temp = record.get("type")
            if temp:
                all_types.append(temp)
        return temp
