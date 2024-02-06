from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
import psycopg2
import os
import psutil
from sqlalchemy import event


def modify_pool_settings_dynamically(engine, pool_config):
    if pool_config.get("pid_based", False):

        @event.listens_for(engine, "before_cursor_execute")
        def before_cursor_execute(
            conn, cursor, statement, parameters, context, executemany
        ):

            num_pids = len(psutil.pids())

            dyn_pool_size = min(
                int(pool_config["pid_pool_factor"] * num_pids),
                pool_config["pool_limit"],
            )
            dyn_overflow = min(
                int(pool_config["pid_overflow_factor"] * num_pids),
                pool_config["overflow_limit"],
            )

            engine.pool.size = dyn_pool_size
            engine.pool._max_overflow = dyn_overflow

    return


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


def get_engine(database_uri, pool=False, pool_config={}):
    # don't pool - multiprocessing
    kwargs = {"poolclass": NullPool, "creator": connect}
    if pool:
        kwargs = {
            "pool_pre_ping": True,
            "pool_size": pool_config["pool_size"],
            "max_overflow": pool_config["max_overflow"],
            "pool_timeout": pool_config["pool_timeout"],
            "pool_recycle": pool_config["pool_recycle"],
            "creator": connect,
        }
    engine = create_engine(database_uri, **kwargs)

    if pool and pool_config.get("dynamic_pooling", False):
        modify_pool_settings_dynamically(engine, pool_config)

    return engine


def get_session(database_uri):
    # session can be created by calling session_maker

    engine = get_engine(database_uri)
    session_maker = sessionmaker(autocommit=False, autoflush=True, bind=engine)
    session = session_maker()
    return session


def get_session_with_engine(engine):

    # logging.info(f"pool id: {id(engine.pool)}")
    # logging.info(f"pool check in id: {engine.pool.checkedin()}")
    # logging.info(f"pool check out: {engine.pool.checkedout()}")

    session_maker = sessionmaker(autocommit=False, autoflush=True, bind=engine)
    session = session_maker()
    return session
