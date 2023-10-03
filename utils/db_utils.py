import glob
import importlib
import os
import logging
import inspect
from sqlalchemy import inspect as sql_inspect

# ati code imports
import utils.config_utils as cu
from core.db import get_engine
from models.db_session import DBSession
import models.misc_models as mm


def create_all_tables() -> None:
    all_files = glob.glob("models/*.py")
    for file in all_files:
        module = file.split(".")[0]
        module = module.replace("/", ".")
        print(f"looking for models in module: {module}")
        try:
            models = importlib.import_module(module)
            models.Base.metadata.create_all(bind=get_engine(os.getenv("FM_DATABASE_URI")))
            print(f"created tables from {module}")
        except Exception as e:
            print(f"failed to create tables from {module}, {e}")
    return


def create_table(model) -> None:
    model.__table__.metadata(bind=get_engine(os.getenv("FM_DATABASE_URI")))
    return


def get_all_table_names():
    inspector = sql_inspect(get_engine(os.getenv("FM_DATABASE_URI")))
    all_table_names = inspector.get_table_names("public")
    return all_table_names


def maybe_add_plugin_user(fm_mongo, fu_db):
    create_col_kwargs = getattr(cu.CreateColKwargs, "capped_default")
    fm_mongo.create_collection("plugin_info", fu_db, **create_col_kwargs)
    fm_mongo.add_validator(
        "plugin_info", fu_db, getattr(cu.PluginConfigValidator, "plugin_info")
    )
    c = fm_mongo.get_collection("plugin_info", fu_db)
    if c.count_documents(filter={}) == 0:
        c.insert_one(cu.PluginConfigDefaults.plugin_info)
        print(f"Created default plugin auth details")


def maybe_add_default_admin_user(fm_mongo):
    fm_mongo.create_database("frontend_users")
    fu_db = fm_mongo.get_database("frontend_users")
    fm_mongo.create_collection("user_details", fu_db)
    fm_mongo.add_validator(
        "user_details", fu_db, getattr(cu.FrontendUsersValidator, "user_details")
    )
    c = fm_mongo.get_collection("user_details", fu_db)
    c.create_index("name", unique=True)
    user_query = {
        "name": cu.DefaultFrontendUser.admin["name"],
    }
    if c.find_one(filter=user_query) is None:
        c.insert_one(cu.DefaultFrontendUser.admin)
        print(f"Created default user")

    maybe_add_plugin_user(fm_mongo, fu_db)
    is_admin_password_set_to_default(fm_mongo, fu_db)


def is_admin_password_set_to_default(fm_mongo, fu_db):
    admin_username = cu.DefaultFrontendUser.admin["name"]
    user_query = {
        "name": admin_username,
    }
    user_details_db = fm_mongo.get_frontend_user_details(user_query)
    if (
        user_details_db["hashed_password"]
        == cu.DefaultFrontendUser.admin["hashed_password"]
    ):
        with DBSession() as dbsession:
            default_password_log = (
                f"Please change password for user: {admin_username}, reason: weak password"
            )
            dbsession.add_notification(
                [],
                default_password_log,
                mm.NotificationLevels.alert,
                mm.NotificationModules.generic,
            )


def create_mongo_collection(fm_mongo, fc_db, collection_name):
    create_col_kwargs = getattr(cu.CreateColKwargs, "capped_default")
    fm_mongo.create_collection(collection_name, fc_db, **create_col_kwargs)
    fm_mongo.add_validator(
        collection_name, fc_db, getattr(cu.ConfigValidator, collection_name)
    )
    c = fm_mongo.get_collection(collection_name, fc_db)

    default_config = getattr(cu.ConfigDefaults, collection_name)
    query = {}
    if c.find_one(query) is None:
        c.insert_one(default_config)
        logging.getLogger("configure_fleet").info(
            f"Set config: {collection_name} to default"
        )
    else:
        logging.getLogger("configure_fleet").info(
            f"Retaining config: {collection_name} as it is"
        )


def setfm_mongo_config(fm_mongo):
    maybe_add_default_admin_user(fm_mongo)
    fm_mongo.create_database("fm_config")
    fc_db = fm_mongo.get_database("fm_config")
    config_val_members = inspect.getmembers(cu.ConfigValidator)
    all_collection_names = []
    for val in config_val_members:
        if not val[0].startswith("__"):
            all_collection_names.append(val[0])

    for collection_name in all_collection_names:
        create_mongo_collection(fm_mongo, fc_db, collection_name)
