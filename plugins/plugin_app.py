from fastapi import FastAPI
import os
import toml

app = FastAPI()

plugin_config = toml.load(os.path.join(os.getenv("FM_CONFIG_DIR"), "plugin_config.toml"))
all_plugins = plugin_config["all_plugins"]


if "ies" in all_plugins:
    from .ies import ies_comms

    app.include_router(ies_comms.router)
