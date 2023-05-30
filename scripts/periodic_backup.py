import time
import logging
import os
from sqlalchemy import inspect
from sqlalchemy import create_engine
from sqlalchemy import MetaData
from sqlalchemy.orm import sessionmaker
import pandas as pd
import datetime
import shutil
import redis
import json

# ati code imports
from core.db import get_engine


def backup_data():
    logging.getLogger().info("Starting periodic data_backup")
    fm_backup_path = os.path.join(os.getenv("FM_STATIC_DIR"), "data_backup")
    start_time = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    current_data = f"{start_time}_data"

    redis_conn = redis.from_url(os.getenv("FM_REDIS_URI"))
    redis_conn.set("current_data_folder", current_data)

    if not os.path.exists(fm_backup_path):
        os.mkdir(fm_backup_path)
    os.mkdir(os.path.join(fm_backup_path, current_data))

    logs_save_path = os.path.join(fm_backup_path, current_data, "logs")

    with open(os.path.join(fm_backup_path, current_data, "info.txt"), "w") as info_file:
        info_file.write(os.getenv("FM_IMAGE_INFO"))

    redis_conn = redis.from_url(
        os.getenv("FM_REDIS_URI"), encoding="utf-8", decode_responses=True
    )

    plugin_db_init = False
    while not plugin_db_init:
        plugin_db_init = (
            False
            if redis_conn.get("plugins_workers_db_init") is None
            else json.loads(redis_conn.get("plugins_workers_db_init"))
        )
        if not plugin_db_init:
            logging.info("Will wait for plugin db init")
            time.sleep(20)

    # get all databases
    all_databases = [
        datnames[0]
        for datnames in get_engine(os.getenv("FM_DATABASE_URI"))
        .execute("SELECT datname FROM pg_database;")
        .fetchall()
    ]

    valid_dbs = []
    for database_name in all_databases:
        if not any(excludable in database_name for excludable in ["postgres", "template"]):
            db_backup_path = os.path.join(fm_backup_path, current_data, database_name)
            os.mkdir(os.path.join(db_backup_path))
            logging.info(f"Will periodically backup {database_name} db")
            valid_dbs.append(database_name)

    while True:
        for db_name in valid_dbs:
            path_to_db = os.path.join(os.getenv("FM_DATABASE_URI"), db_name)
            db_engine = create_engine(path_to_db)
            inspector = inspect(db_engine)
            all_tables = inspector.get_table_names("public")
            session_maker = sessionmaker(autocommit=False, autoflush=True, bind=db_engine)
            session = session_maker()

            for table in all_tables:
                try:
                    metadata = MetaData(db_engine)
                    metadata.reflect()
                    model = metadata.tables[table]
                    column_names = [column.name for column in inspect(model).c]
                    data = session.query(model).all()
                    df = pd.DataFrame(data, columns=column_names)
                    csv_save_path = os.path.join(
                        fm_backup_path, current_data, db_name, f"{model}.csv"
                    )
                    df.to_csv(csv_save_path, index=False)
                except:
                    pass

            session.close()

        try:
            shutil.rmtree(logs_save_path)
        except:
            pass

        shutil.copytree(os.getenv("FM_LOG_DIR"), logs_save_path)
        logging.getLogger("status_updates").info("Backed up data")
        cleanup_data()
        time.sleep(120)


def get_directory_size(directory):
    total_size = 0
    for path, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(path, file)
            total_size += os.path.getsize(file_path)

    total_size_mb = total_size / (1024 * 1024)
    return total_size_mb


def sort_and_remove_directories(directory, target_size):
    directories = [os.path.join(directory, name) for name in os.listdir(directory)]
    directories.sort()

    current_size = 0
    for dir_path in directories:
        dir_size = get_directory_size(dir_path)
        if current_size + dir_size <= target_size:
            shutil.rmtree(dir_path)
            current_size += dir_size
        else:
            break


def cleanup_data(db_keep_size=1000):
    fm_backup_path = os.path.join(os.getenv("FM_STATIC_DIR"), "data_backup")
    data_backup_size = get_directory_size(fm_backup_path)
    lst = os.listdir(fm_backup_path)
    number_files = len(lst)
    if number_files > 1:
        sort_and_remove_directories(fm_backup_path, data_backup_size - db_keep_size)
