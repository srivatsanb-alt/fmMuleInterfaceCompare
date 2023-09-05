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
        database=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        host=os.getenv("POSTGRES_HOST"),
        **keepalive_kwargs,
    )


def get_engine(database_uri):
    # don't pool - multiprocessing
    engine = create_engine(
        database_uri,
        poolclass=NullPool,
        creator=connect,
        # pool_pre_ping=True,
        # pool_size=100,
        # max_overflow=30,
    )
    return engine


def get_session(database_uri):
    # session can be created by calling session_maker
    session_maker = sessionmaker(
        autocommit=False, autoflush=True, bind=get_engine(database_uri)
    )
    session = session_maker()
    return session
