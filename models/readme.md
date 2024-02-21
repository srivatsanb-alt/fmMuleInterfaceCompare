## DB schema, model definitions ##

This directory contains the definitions of pydantic models used by [FastAPI](https://fastapi.tiangolo.com/) application and [SQLAlchemy](https://www.sqlalchemy.org/) models that can be used to access, perform CRUD operations on the tables.

Explaining base models and fleet models in this doc. The same is extendable to all other schema models


## Base models ##

1. [Base](https://docs.sqlalchemy.org/en/13/orm/extensions/declarative/basic_use.html) defined in [base_models](base_models.py) which all the sqlalchemy models should inherit. Any new model added to any file inside the folder models, which inherits Base class will be created in the database during the course of [fm_init](../fm_init.py). Please check the method create_all_tables in [db utils](../utils/db_utils.py)

2. [TimestampMixin](#timestampmixin)

3. [Fleet models](#fleet-models)

4. [Use of primaryjoin, secondary join](#use-of-primaryjoin-secondary-join)

5. [Use of association table](#use-of-association-table)

6. [Use of mongo db](#use-of-mongo-db)


## TimestampMixin ##

Any models that inherits class [TimestampMixin](base_models.py#classTimestampMixin), will have created_at, updated_at column added to its respective table. This is to keep track when an entry was added to the DB, when it was last updated.


## Fleet models ##

All the schema of the assets pertaining to the fleet is defined in [fleet_models](fleet_models.py). Schema for tables sherpas, fleets, maps etc are defined in this file.You would also be able to relationship between the assets defined in this file.


For instance, [Fleet](fleet_models.py#classFleet(Base)) has one-to-many relation [Sherpa](fleet_models.py#classSherpa(Base)), [Stations](fleet_models.py#classStation(Base)), one-one relationship with asset Map.

One fleet can have multiple sherpas, stations whereas can only have one set of map files. Sherpa has a one-to-one relationship to fleet. One sherpa can be part of only one fleet

Each [Sherpa](fleet_models.py#classSherpa(Base)) has one-to-one relationship to [SherpaStatus](fleet_models.py#classSherpaStatus(TimestampMixin,Base)). 

We store asset details which don't change frequently to table sherpas [Sherpa](fleet_models.py#classSherpa(Base)) table(hardware id , name, ip_address etc). Other details which correspond to the sherpa state (disabled, inducted, trip_id), which changes dynamically are part of the table sherpastatus.


The relationships are defined to enable ease of use. For instance, to retrive all the sherpas in a fleets. 

```
with DBSession() as dbsession:
    fleet = dbsession.get_fleet("fleetABC")
    all_sherpas: List[Sherpas] = fleet.sherpas
```

## Use of primaryjoin, secondary join ##

Check the section [Specifying Alternate Join Conditions](https://docs.sqlalchemy.org/en/20/orm/join_conditions.html). 

You can see how we use of self-referential relationship along with primaryjoin, secondary join used in schema definition of [ExclusionZone](visa_models.py#ExclusionZone(Base,TimestampMixin))


## Use of association table ## 

When definiing many-to-many relationship between two classes, we will have to define a association table The association table will have foreign key constraints established that refer to the two entity tables on either side of the relationship. 

You can notice the usage of many-to-many relationship between [ExclusionZone](visa_models.py#classExclusionZone(Base,TimestampMixin)) and [Sherpa](fleet_models.py#classSherpa(Base)) defined along with association table [VisaAssignment](visa_models.py#classVisaAssignment(Base,TimestampMixin))


Check the section[Many To Many
](https://docs.sqlalchemy.org/en/20/orm/basic_relationships.html)


## Use of mongo db ## 

We use mongo db to store unstructured data such as config. We use a package called [pymongo](https://pypi.org/project/pymongo/) to connect to mongo db.

Mongo db can be accessed using the custom class [FMMongo](mongo_client.py#classFMMongo).
```
with FMMongo() as fm_mongo:
    optimal_dispatch_config = fm_mongo.get_document_from_fm_config(
        "optimal_dispatch"
    )
```

Though we use mongo db to store unstructured data, we do add some validators to ensure sanity of the data added/updated to mongo db.

We have multiple databases like fm_config, frontend_users, plugin_config etc. Each database will have multiple collections, each collection can have multiple documents.

Any member in class [ConfigValidator](../utils/config_utils.py#classConfigValidator) if not present in the database fm_config is created during the course of [fm_init](../fm_init.py) by the method [setfm_mongo_config](../utils/db_utils.py#defsetfm_mongo_config(fm_mongo)).

The collections are created, schema validations are added using the definition present in [ConfigValidator](../utils/config_utils.py#classConfigValidator) .Default document is added to collection using values present in [ConfigDefaults](../utils/config_utils.py#classConfigDefaults). By default we cap the number of documents in any collection to 1. This is done using [CreateColKwargs](../utils/config_utils.py#classCreateColKwargs)

Similarly collections pertaining to plugin would be defined under [PluginConfigValidator](../utils/config_utils.py#classPluginConfigValidator)