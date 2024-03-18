import os


# ati code imports
from core.db import get_engine


def get_db_pool_config():
    ## Have made pool limits a factor for PSQL_MAX_CONNECTIONS
    pool_config = {
        "pool_size": 30,
        "max_overflow": 10,
        "pool_timeout": 10,
        "pool_recycle": 30,
        "pool_limit": int(int(os.getenv("PSQL_MAX_CONNECTIONS")) / 5),
        "overflow_limit": int(int(os.getenv("PSQL_MAX_CONNECTIONS")) / 10),
        "dynamic_pooling": True,
        "pid_based": True,
        "pid_pool_factor": 0.25,
        "pid_overflow_factor": 0.1,
    }
    return pool_config


engine = get_engine(
    os.path.join(os.getenv("FM_DATABASE_URI"), os.getenv("PGDATABASE")),
    pool=True,
    pool_config=get_db_pool_config(),
)
