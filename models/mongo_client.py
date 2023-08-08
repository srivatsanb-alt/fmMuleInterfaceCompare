import pymongo as pm
import os
from utils.config_utils import CONFIG_VIEW_PERMISSION_LEVELS


def get_mongo_client(uri: str):
    mongo_client = pm.MongoClient(uri)
    return mongo_client


class FMMongo:
    def __init__(self, uri=None):
        if uri is None:
            uri = os.getenv("FM_MONGO_DATABASE_URI")
        self.mongo_client = get_mongo_client(uri)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.mongo_client.close()

    def list_database_names(self):
        return self.mongo_client.list_database_names()

    def create_database(self, db_name):
        if db_name not in self.list_database_names():
            db = self.mongo_client[db_name]
            db.create_collection("dummy", capped=True, size=1, max=1)
            col = self.get_collection("dummy", db)
            col.insert_one({})
        return

    def get_database(self, db_name):
        if db_name in self.list_database_names():
            return self.mongo_client[db_name]
        raise Exception(f"Database {db_name} not found")

    def add_validator(self, collection_name, db, validator={}):
        db.command("collMod", collection_name, validator=validator)

    def create_collection(self, collection_name, db, **kwargs):
        try:
            db.create_collection(collection_name, **kwargs)
            return True
        except Exception as e:
            print(f"Unable to create collection {collection_name}, Exception: {e}")
        return False

    def get_collection(self, collection_name, db):
        if collection_name in db.list_collection_names():
            return db[collection_name]
        raise Exception(f"Collection {collection_name} not yet created")

    def create_index(var, collection, is_unique=True):
        collection.create_index(var, unique=is_unique)

    def add_permission_level(self, level, **kwargs):
        level_int = getattr(CONFIG_VIEW_PERMISSION_LEVELS, level.upper(), None)
        if level_int is None:
            raise Exception("Invalid permission level")
        kwargs.update({"permission_level": level_int})

    def get_all_collection_names(self, db_name):
        return self.mongo_client[db_name].list_collection_names()

    def get_all_documents(self, collection):
        return collection.find()

    def get_documents_with_filter(self, collection, filter, display_filter={"_id": 0}):
        return collection.find(filter, display_filter)

    def get_documents_with_permission_level(self, collection, permission_level):
        filter = {"permission_level": {"$lte": permission_level}}
        return self.get_documents_with_filter(collection, filter)

    def get_all_document_types(self, collection, permission_level=None):
        filter = {}
        if permission_level is not None:
            filter = {"permission_level": {"$lt": permission_level}}
        all_types = []
        display_filter = {"type": 1, "_id": 0}
        cursor = self.get_documents_with_filter(collection, filter, display_filter)
        for record in cursor:
            temp = record.get("type")
            if temp:
                all_types.append(temp)
        return temp

    def get_collection_from_fm_config(self, collection_name):
        fc_db = self.mongo_client.get_database("fm_config")
        temp = self.get_collection(collection_name, fc_db).find_one()
        if temp is None:
            raise Exception(f"No {collection_name} config")
        return temp
