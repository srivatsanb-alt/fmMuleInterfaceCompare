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

# ati code imports
from core.db import get_engine
from models.mongo_client import FMMongo


def prune_unused_images(backup_config):
    if backup_config["prune_unused_images"] is True:
        temp = backup_config["prune_images_used_until_h"]
        if os.system(f"docker image prune -f --filter 'until={temp}h'") == 0:
            logging.getLogger("misc").info(f"Pruned old({temp}h) docker images")
        else:
            logging.getLogger("misc").warning(f"Unable to prune old({temp}h) docker images")


def backup_data():
    with FMMongo() as fm_mongo:
        backup_config = fm_mongo.get_document_from_fm_config("data_backup")

    logging.getLogger().info("Starting periodic data_backup")
    fm_backup_path = os.path.join(os.getenv("FM_STATIC_DIR"), "data_backup")
    start_time = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    current_data = f"{start_time}_data"
    redis_conn = redis.from_url(os.getenv("FM_REDIS_URI"))
    redis_conn.set("current_data_folder", current_data)
    run_backup_path = os.path.join(fm_backup_path, current_data)
    if not os.path.exists(fm_backup_path):
        os.mkdir(fm_backup_path)
    os.mkdir(run_backup_path)
    logs_save_path = os.path.join(run_backup_path, "logs")
    with open(os.path.join(run_backup_path, "info.txt"), "w") as info_file:
        info_file.write(os.getenv("FM_IMAGE_INFO"))

    # wait for plugin init
    time.sleep(45)

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
            db_backup_path = os.path.join(
                fm_backup_path, current_data, f"{database_name}_db"
            )
            os.mkdir(os.path.join(db_backup_path))
            logging.info(f"Will periodically backup {database_name} db")
            valid_dbs.append(database_name)

    freq = 60
    last_prune_time = time.time()
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
                        fm_backup_path, current_data, f"{db_name}_db", f"{model}.csv"
                    )
                    df.to_csv(csv_save_path, index=False)
                except:
                    pass

            session.close()

        try:
            shutil.rmtree(logs_save_path)
        except:
            pass

        docker_cp_returncod = os.system(
            f"docker cp fm_plugins:/app/plugin_logs {run_backup_path}"
        )
        if docker_cp_returncod != 0:
            logging.getLogger("misc").warning(f"Unable to copy fm_plugin logs")

        # prune images every 30 minutes
        if time.time() - last_prune_time > 1800:
            prune_unused_images(backup_config)
            last_prune_time = time.time()

        shutil.copytree(os.getenv("FM_LOG_DIR"), logs_save_path)
        logging.getLogger("misc").info(f"Backed up data")

        try:
            # default keep size is 1000MB
            keep_size_mb = backup_config["keep_size_mb"]
            cleanup_data(current_data, keep_size_mb)

        except Exception as e:
            logging.getLogger("misc").error(
                f"couldn't cleanup old backed up data, exception: {e}"
            )
        time.sleep(freq)


def get_directory_size(directory):
    total_size = 0
    for path, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(path, file)

            # returns size in bytes
            total_size += os.path.getsize(file_path)

    total_size_mb = total_size / (1024 * 1024)
    return total_size_mb


def sort_dir_list(list_dir):
    TIME_FORMAT = "%Y-%m-%d-%H-%M-%S"
    for dir in list_dir:
        try:
            datetime.datetime.strptime(dir.rsplit("_", 1)[0], TIME_FORMAT)
        except Exception as e:
            logging.getLogger("misc").info(
                f"Directory name not in valid format, ignoring {dir}, cannot be sorted according to timestamp, exception: {e}"
            )
            list_dir.remove(dir)

    list_dir.sort(
        key=lambda date: datetime.datetime.strptime(date.rsplit("_", 1)[0], TIME_FORMAT)
    )


def sort_and_remove_directories(directory, target_size, current_data):

    list_dir = os.listdir(directory)

    # cannot delete current data folder
    list_dir.remove(current_data)
    sort_dir_list(list_dir)

    directories = [os.path.join(directory, name) for name in list_dir]
    current_size = 0
    for dir_path in directories:
        dir_size = get_directory_size(dir_path)
        if current_size + dir_size <= target_size:
            shutil.rmtree(dir_path)
            current_size += dir_size
            logging.getLogger("misc").warning(f"Deleted {dir_path}")


def cleanup_data(current_data, keep_size_mb=1000):
    fm_backup_path = os.path.join(os.getenv("FM_STATIC_DIR"), "data_backup")
    data_backup_size = get_directory_size(fm_backup_path)

    # delete if data_backup size greater than keep_size
    if data_backup_size > keep_size_mb:
        logging.getLogger("misc").warning(
            f"data_backup folder size ({data_backup_size} mb) greater than {keep_size_mb} mb"
        )
        lst = os.listdir(fm_backup_path)
        number_files = len(lst)
        if number_files > 1:
            logging.getLogger("misc").info(
                "will check if some old backed up data can be deleted"
            )
            sort_and_remove_directories(
                fm_backup_path, data_backup_size - keep_size_mb, current_data
            )
        else:
            logging.getLogger("misc").warning("no older backed up data to delete")
