import os
import toml


def read_config():
    return toml.load(os.getenv("FM_CONFIG_DIR") + "/config.toml")


def get_fleet_mode(config=None):
    if not config:
        config = read_config()
    return config["fleet"].get("mode")


def get_handler_class(config=None):
    if not config:
        config = read_config()
    return config["fleet"].get("handler_class")


def get_handler_package(config=None):
    if not config:
        config = read_config()
    return config["fleet"].get("handler_package")
