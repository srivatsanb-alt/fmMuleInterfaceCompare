import os
import redis
import json
from typing import List


def get_other_loggers():
    others_loggers = []
    others_loggers.append("uvicorn")
    others_loggers.append("misc")
    others_loggers.append("optimal_dispatch")
    others_loggers.append("configure_fleet")
    others_loggers.append("status_updates")
    others_loggers.append("visa")
    others_loggers.append("mfm_updates")
    others_loggers.append("misc")
    others_loggers.append("control_module_router")
    others_loggers.append("process_times")

    return others_loggers


def add_log_formatter(log_config):
    log_config.update(
        {
            "formatters": {
                "default": {
                    "format": "%(asctime)s - %(levelname)s [%(funcName)s] %(message)s",
                    "datefmt": "%Y-%m-%d %H:%M:%S",
                }
            }
        }
    )
    return log_config


def add_logger(log_name: str, log_config: dict, propagate=0):
    LOG_LEVEL = "INFO"
    handler_name = log_name
    new_logger = {
        "qualname": log_name,
        "level": LOG_LEVEL,
        "handlers": [handler_name],
        "propagate": propagate,
    }

    loggers = log_config["loggers"]
    loggers.update({log_name: new_logger})


def add_handler(log_name: str, log_config: dict):
    MAX_LOG_SIZE = 2e8
    log_file = os.path.join(os.getenv("FM_LOG_DIR"), f"{log_name}.log")

    if log_name == "":
        log_file = os.path.join(os.getenv("FM_LOG_DIR"), "fleet_manager.log")

    new_handler = {
        "class": "logging.handlers.RotatingFileHandler",
        "formatter": "default",
        "filename": log_file,
        "maxBytes": MAX_LOG_SIZE,
        "backupCount": 1,
    }
    handlers = log_config["handlers"]
    handlers.update({log_name: new_handler})


def set_log_config_dict(all_sherpas: List[str] = []):

    all_loggers = []

    # need root logger
    all_loggers.append("")

    for sherpa_name in all_sherpas:
        all_loggers.append(sherpa_name)

    all_loggers.extend(get_other_loggers())

    log_config = {}

    log_config.update({"version": 1})
    log_config.update({"loggers": {}})
    log_config.update({"handlers": {}})
    add_log_formatter(log_config)

    for log_name in all_loggers:
        add_handler(log_name, log_config)
        add_logger(log_name, log_config)

    redis_conn = redis.from_url(os.getenv("FM_REDIS_URI"))
    redis_conn.set("log_dict_config", json.dumps(log_config))


def get_log_config_dict():
    redis_conn = redis.from_url(os.getenv("FM_REDIS_URI"))
    log_config_dict = redis_conn.get("log_dict_config")

    if log_config_dict is None:
        set_log_config_dict()
        log_config_dict = redis_conn.get("log_dict_config")

    return json.loads(log_config_dict)
