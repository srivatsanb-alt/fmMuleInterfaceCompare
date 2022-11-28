from sqlalchemy import create_engine
import os
import time


def init_db(name, models):
    create_db(name, models)


def create_db(database_name, models):
    path_to_db = os.path.join(os.getenv("FM_DATABASE_URI"), database_name)

    # database might exsist already
    try:
        engine = create_engine(os.getenv("FM_DATABASE_URI"))
        with engine.connect() as conn:
            conn.execute("commit")
            conn.execute(f"CREATE DATABASE {database_name}")

        time.sleep(2)

    except Exception as e:
        pass

    engine_db = create_engine(path_to_db)

    # create the required tables
    for model in models:
        model.__table__.create(bind=engine_db, checkfirst=True)
