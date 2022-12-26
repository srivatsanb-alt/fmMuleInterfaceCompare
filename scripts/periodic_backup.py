import time
import logging
import os
from sqlalchemy import inspect
from sqlalchemy import create_engine
from models.base_models import Base
from sqlalchemy.orm import sessionmaker
from core.db import engine
import pandas as pd
import datetime
import shutil


def backup_data():
    logging.getLogger().info("Starting periodic data_backup")
    fm_backup_path = os.path.join(os.getenv("FM_MAP_DIR"), "data_backup")
    start_time = datetime.datetime.now().strftime("%d-%m-%Y-%H-%M-%S")
    current_data = f"{start_time}_data"

    if not os.path.exists(fm_backup_path):
        os.mkdir(fm_backup_path)
    os.mkdir(os.path.join(fm_backup_path, current_data))

    # get all databases
    all_databases = [
        datnames[0]
        for datnames in engine.execute("SELECT datname FROM pg_database;").fetchall()
    ]

    valid_dbs = []
    for database_name in all_databases:
        if not any(excludable in database_name for excludable in ["postgres", "template"]):
            logging.getLogger().info(f"Will periodically backup database: {database_name}")
            os.mkdir(os.path.join(fm_backup_path, current_data, database_name))
            valid_dbs.append(database_name)

    logs_save_path = os.path.join(fm_backup_path, current_data, "logs")

    with open(os.path.join(fm_backup_path, current_data, "info.txt"), "w") as info_file:
        info_file.write(os.getenv("FM_IMAGE_INFO"))

    while True:
        for db_name in valid_dbs:
            path_to_db = os.path.join(os.getenv("FM_DATABASE_URI"), db_name)
            db_engine = create_engine(path_to_db)
            inspector = inspect(db_engine)
            all_tables = inspector.get_table_names("public")
            session_maker = sessionmaker(autocommit=False, autoflush=True, bind=engine)
            session = session_maker()

            for table in all_tables:
                try:
                    model = Base.metadata.tables[table]
                    column_names = [column.name for column in inspect(model).c]
                    data = session.query(model).all()
                    df = pd.DataFrame(data, columns=column_names)
                    csv_save_path = os.path.join(
                        fm_backup_path, current_data, db_name, f"{model}.csv"
                    )
                    df.to_csv(csv_save_path, index=False)
                except:
                    pass

        try:
            shutil.rmtree(logs_save_path)
        except:
            pass

        shutil.copytree(os.getenv("FM_LOG_DIR"), logs_save_path)
        logging.getLogger("status_updates").info("Backed up data")
        time.sleep(120)
