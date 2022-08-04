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

    def __init__(self):
        raise NotImplementedError("Config class cannot be instantiated")

    @classmethod
    def read_config(cls):
        return toml.load(os.getenv("FM_CONFIG_DIR") + "/config.toml")

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
    def get_handler_package(cls):
        if not cls.config:
            cls.config = cls.read_config()
        return cls.config["fleet"].get("handler_package", "handlers.default.handlers")

    @classmethod
    def get_api_version(cls):
        if not cls.config:
            cls.config = cls.read_config()
        return cls.config["fleet"].get("api_version", "v1")


if __name__ == "__main__":
    d = {"a": [1, 2, 3], "b": {"c": 2, "d": {"e": 3}, "f": {"g": [4, 5]}}}
    fd = flatten_config(d)
    print(fd)
