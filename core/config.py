import os
import toml


def read_config():
    return toml.load(os.getenv("HIVEMIND_CONFIG_DIR") + "/config.toml")


def get_fleet_mode(config):
    return config["fleet"]["mode"]


def get_handler_class(config):
    return config["fleet"]["handler_class"]


def get_handler_package(config):
    return config["fleet"]["handler_package"]
