from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
import psycopg2
import os


def connect():
    keepalive_kwargs = {
        "keepalives": 1,
        "keepalives_idle": 60,
        "keepalives_interval": 10,
        "keepalives_count": 5,
    }

    return psycopg2.connect(
        database=os.getenv("PGDATABASE"),
        host=os.getenv("PGHOST"),
        user=os.getenv("PGUSER"),
        password=os.getenv("PGPASSWORD"),
        **keepalive_kwargs,
    )


def get_engine(database_uri, pool=False):
    # don't pool - multiprocessing
    kwargs = {"poolclass": NullPool, "creator": connect}
    if pool:
        kwargs = {
            "pool_pre_ping": True,
            "pool_size": 50,
            "max_overflow": 30,
            "pool_timeout": 10,
            "creator": connect,
        }
    engine = create_engine(database_uri, **kwargs)
    return engine


def get_session(database_uri, pool=False):
    # session can be created by calling session_maker
    session_maker = sessionmaker(
        autocommit=False, autoflush=True, bind=get_engine(database_uri, pool)
    )
    session = session_maker()
    return session
