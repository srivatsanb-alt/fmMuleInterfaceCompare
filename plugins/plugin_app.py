import uvicorn
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


def get_uvicorn_config():
    uvi_config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PLUGIN_PORT")),
        log_level="debug",
        log_config=os.path.join(os.getenv("FM_CONFIG_DIR"), "logging.conf"),
        reload=True,
    )
    return uvi_config


def main():
    config = get_uvicorn_config()
    server = uvicorn.Server(config)
    server.run()


if __name__ == "__main__":
    main()
