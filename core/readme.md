# Interaction with DB #

We use ORM called [sqlalchemy](https://www.sqlalchemy.org/) to connect to the postgres database

## Get a session ## 

Session is the in-memory snap-shot of the data in the DB

1. We have defined a custom class DBSession(../models/db_session.py) which can be used to obtaine a sqlalchemy session, access the tables present in the DB. All the sqlalchemy models have been in files like [fleet_models](../models/fleet_models.py), [trip_models](../models/trip_models.py) etc.

```
from models.db_session import DBSession

with DBSession() as dbsession:
    ### do whatever changes needs to be done
    dbsession.session.query(...)
    dbsession.add_to_session(new_object)
```

2. The __entry__ and __exit__ method have been added to the class DBSession in order to follow [Unit of work](#unit-of-work). Donot commit changes to the DB if there is a traceback.

2. Openning and closing DB connections can be costly, to reduce the same we use DB pooling wherever possible. Pooling will be of useful where the usage is traffic dependent. We use pooled connections in FastAPI app, handlers. 

3. To obtain a session with pooled connection use the global variable engine defined in [common.py](../core/common.py). For more details check [Dynamic pooling](#dynamic-pooling)

```
import core.common as ccm

with DBSession(engine=ccm.engine) as dbsession:
    ### do whatever changes needs to be done
    ## dbsession.session.query()..
    ## dbsession.add_to_session(new_object)
```

## Unit of work ##

Either commit all the updates or commit None.

For example, if a trip needs to be successfully booked. We should be able to create a entry in trip table, another entry in pending_trip table. In this case we would commit changes only if both the operations succeeded. The changes made to database session will be rolled back even if one of the operations fails.

```
with Session(engine) as session:
    session.begin()
    try:
        session.add(some_object)
        session.add(some_other_object)
    except:
        session.rollback()
        raise
    else:
        session.commit()
```

If all operations succeed, the Session.commit() method will be called, but if any exceptions are raised, the Session.rollback() method will be called so that the transaction is rolled back immediately, before propagating the exception outward.

## Postgres server ##

The postgres server is hosted inside the container fleet_db. 

We almost use the default postgres config. Only change that we make is that we set the max number of connections that be openned simultaneously to higher number. This is configurable.

Please check [psql_connection_setting](../scripts/psql_connection_settings.py) and the method set_max_connections from (../scripts/fleet_orchestrator.sh) to see how the max_connections is obtained from config, set in postgres server.


## Dynamic pooling ##

The default pool_config we used to create a connection pool is provided in [core_common](../core/common.py)

Number of active connections in the DB pool is dynamic, is a factor of number of PIDs running inside the container.

For instance, for a small fleet with two sherpas, number of pid would be around 20. The number of connections in a pool would be 4 (0.2*20). A pool would be having 4 connections. A different pool of connections will be used by different  modules like handlers, uvicorn app etc. We will be having 8 connections in the pool being shared by 15-20 processes.

For a bigger fleet, the number of pids would be higher, number of connections in each pool would also get scaled propotionally.

MAX number of connections in a pool is limited by PSQL_MAX_CONNECTIONS (configurable parameter manually set based on fleet size). No pool can have connections more than one-fifth of max connections that can be opened with the PSQL server.

```
pool_config = {
        "pool_size": 30,
        "max_overflow": 10,
        "pool_timeout": 10,
        "pool_recycle": 30,
        "pool_limit": int(int(os.getenv("PSQL_MAX_CONNECTIONS")) / 5),
        "overflow_limit": int(int(os.getenv("PSQL_MAX_CONNECTIONS")) / 10),
        "dynamic_pooling": True,
        "pid_based": True,
        "pid_pool_factor": 0.2,
        "pid_overflow_factor": 0.1,
}
```

We don't pool connections in processes forked of main.py. Number of connections required by the periodic scripts started in [main.py](../main.py) would be constant, doesn't require pooling.  If we need to pool DB connections for forked of processes in the future please check the topic "Using Connection Pools with Multiprocessing or os.fork()" (https://docs.sqlalchemy.org/en/20/core/pooling.html#using-connection-pools-with-multiprocessing-or-os-fork)


## References ## 

1. [Engine Configuration](https://docs.sqlalchemy.org/en/20/core/engines.html)
2. [Session basics](https://docs.sqlalchemy.org/en/20/orm/session_basics.html)