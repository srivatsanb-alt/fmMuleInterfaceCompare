from fastapi import FastAPI
import os
import toml
import json
import redis

plugins_workers_db_init = False
redis_conn = redis.from_url(os.getenv("FM_REDIS_URI"))

# app cannot come up until db and workers are initialised
while not plugins_workers_db_init:
    plugin_init = redis_conn.get("plugins_workers_db_init")
    if plugin_init is not None:
        plugins_workers_db_init = json.loads(plugin_init)

app = FastAPI()

plugin_config = toml.load(os.path.join(os.getenv("FM_CONFIG_DIR"), "plugin_config.toml"))
all_plugins = plugin_config["all_plugins"]


if "ies" in all_plugins:
    from .ies import ies_comms

    app.include_router(ies_comms.router)

if "conveyor" in all_plugins:
    from .conveyor import conveyor_comms

    app.include_router(conveyor_comms.router)

if "summon_button" in all_plugins:
    from .summon_button import summon_comms

    app.include_router(summon_comms.router)
