import os
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
import aioredis
import psycopg2
import redis

from core.settings import settings


aioredis = aioredis.from_url(
    os.getenv("FM_REDIS_URI"), encoding="utf-8", decode_responses=True
)
_redis_instance = redis.from_url(
    os.getenv("FM_REDIS_URI"), encoding="utf-8", decode_responses=True
)


def get_redis():
    return _redis_instance


keepalive_kwargs = {
    "keepalives": 1,
    "keepalives_idle": 60,
    "keepalives_interval": 10,
    "keepalives_count": 5,
}


def connect():
    return psycopg2.connect(
        host=os.getenv("PGHOST"),
        user=os.getenv("PGUSER"),
        password=os.getenv("PGPASSWORD"),
        **keepalive_kwargs
    )


# don't pool - multiprocessing
engine = create_engine(
    settings.FM_DATABASE_URI,
    poolclass=NullPool,
    # pool_pre_ping=True,
    # pool_size=100,
    # max_overflow=30,
    creator=connect,
)

session_maker = sessionmaker(autocommit=False, autoflush=True, bind=engine)
