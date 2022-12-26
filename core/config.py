import importlib
import os
from typing import Dict
import toml


def flatten_config(config: Dict, prefix: str = None):
    flat: Dict = {}
    for key, val in config.items():
        new_key = f"{prefix}.{key}" if prefix else key
        if isinstance(val, dict):
            flat.update(flatten_config(val, new_key))
        else:
            flat[new_key] = val

    return flat


class Config:
    config = {}
    handler_obj = None

    def __init__(self):
        raise NotImplementedError("Config class cannot be instantiated")

    @classmethod
    def read_config(cls):
        return toml.load(os.path.join(os.getenv("FM_CONFIG_DIR"), "fleet_config.toml"))

    @classmethod
    def get_fleet_mode(cls):
        if not cls.config:
            cls.config = cls.read_config()
        return cls.config["fleet"].get("mode", "default")

    @classmethod
    def get_handler_class(cls):
        if not cls.config:
            cls.config = cls.read_config()
        return cls.config["fleet"].get("handler_class", "Handlers")

    @classmethod
    def get_sherpa_port(cls):
        if not cls.config:
            cls.config = cls.read_config()
        return cls.config["fleet"].get("sherpa_port", 5000)

    @classmethod
    def get_http_scheme(cls):
        if not cls.config:
            cls.config = cls.read_config()
        return cls.config["fleet"].get("http_scheme", None)

    @classmethod
    def get_handler_package(cls):
        if not cls.config:
            cls.config = cls.read_config()
        return cls.config["fleet"].get("handler_package", "handlers.default.handlers")

    @classmethod
    def get_handler(cls):
        if not cls.handler_obj:
            handler_package = cls.get_handler_package()
            handler_class = cls.get_handler_class()
            cls.handler_obj = getattr(
                importlib.import_module(handler_package), handler_class
            )()
        return cls.handler_obj

    @classmethod
    def get_api_version(cls):
        if not cls.config:
            cls.config = cls.read_config()
        return cls.config["fleet"].get("api_version", "v1")

    @classmethod
    def get_fleet_comms_params(cls):
        if not cls.config:
            cls.config = cls.read_config()
        return cls.config["fleet"]["comms"]

    @classmethod
    def get_all_fleets(cls):
        if not cls.config:
            cls.config = cls.read_config()
        return cls.config["fleet"]["fleet_names"]

    @classmethod
    def get_all_sherpas(cls):
        if not cls.config:
            cls.config = cls.read_config()
        return cls.config["fleet_sherpas"]

    @classmethod
    def get_simulator_config(cls):
        if not cls.config:
            cls.config = cls.read_config()
        return cls.config["fleet"]["simulator"]

    @classmethod
    def get_optimal_dispatch_config(cls):
        if not cls.config:
            cls.config = cls.read_config()
        return cls.config["optimal_dispatch"]


if __name__ == "__main__":
    d = {"a": [1, 2, 3], "b": {"c": 2, "d": {"e": 3}, "f": {"g": [4, 5]}}}
    fd = flatten_config(d)
    print(fd)
