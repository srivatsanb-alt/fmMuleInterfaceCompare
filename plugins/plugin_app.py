import uvicorn
from fastapi import FastAPI, Depends, APIRouter
import os
import toml
import json
import redis

# ati code imports
import plugins.plugin_dependencies as pdpd


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

router = APIRouter()


# get all available plugins
@router.get("/plugin/api/v1/get_all_plugins")
async def get_all_plugins(user_name=Depends(pdpd.get_user_from_header)):
    if not user_name:
        pdpd.raise_error("Unknown requester", 401)

    plugin_config = toml.load(
        os.path.join(os.getenv("FM_CONFIG_DIR"), "plugin_config.toml")
    )
    all_plugins = plugin_config["all_plugins"]

    return all_plugins


app.include_router(router)

if "ies" in all_plugins:
    from plugins.ies import ies_comms

    app.include_router(ies_comms.router)

if "conveyor" in all_plugins:
    from plugins.conveyor import conveyor_comms

    app.include_router(conveyor_comms.router)

if "summon_button" in all_plugins:
    from plugins.summon_button import summon_comms

    app.include_router(summon_comms.router)


def get_uvicorn_config():
    uvi_config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PLUGIN_PORT")),
        log_level="info",
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
