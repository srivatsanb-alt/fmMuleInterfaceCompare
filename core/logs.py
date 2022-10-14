import logging
import os

from .db import session_maker
from models.fleet_models import Fleet, Sherpa

logging.basicConfig(level=logging.INFO)
FORMATTER = logging.Formatter("%(asctime)s %(levelname)s [%(funcName)s] %(message)s")
loggers = {}


def init_logging():
    logdir = os.environ["FM_LOG_DIR"]
    try:
        os.mkdir(logdir)
    except FileExistsError:
        pass
    setup_root_logger(logdir)
    with session_maker() as db:
        db_fleets = db.query(Fleet).all()
    for fleet in db_fleets:
        init_logging_for_fleet(fleet, logdir)

    # misc loggers
    setup_logger(logdir, "optimal_dispatch")
    setup_logger(logdir, "status_updates")
    setup_logger(logdir, "simulator")
    setup_logger(logdir, "control_router_module")


def init_logging_for_fleet(fleet: Fleet, logdir):
    fleet_name = fleet.name
    fleet_id = fleet.id
    try:
        os.mkdir(logdir + "/" + fleet_name)
    except FileExistsError:
        pass

    # set up fleet-level logger.
    setup_logger_for_fleet(fleet_name, logdir)

    with session_maker() as db:
        db_sherpas = db.query(Sherpa).filter(Sherpa.fleet_id == fleet_id).all()
        for sherpa in db_sherpas:
            # set up sherpa-level logger.
            setup_logger_for_fleet(fleet_name, logdir, sherpa.name)


def setup_root_logger(logdir, level=logging.INFO):
    logger = logging.getLogger()
    logger.setLevel(level)
    logger.handlers.clear()
    handler = logging.FileHandler(logdir + "/fleet_manager.log")
    handler.setFormatter(FORMATTER)
    logger.addHandler(handler)

    loggers["root"] = logger


def setup_logger(logdir, name=None, level=logging.INFO):
    global loggers

    logger = logging.getLogger(f"{name}")
    # propagate messages to fleet logger.

    logger.setLevel(level)
    handler = logging.FileHandler(logdir + f"/{name}.log")
    handler.setFormatter(FORMATTER)
    logger.addHandler(handler)
    loggers[name] = logger


def setup_logger_for_fleet(fleet: str, logdir, name=None, level=logging.INFO):
    global loggers

    if not name:
        name = fleet
    if name == fleet:
        logger = logging.getLogger(fleet)
        # do not propagate messages to root logger
        logger.propagate = False
    else:
        logger = logging.getLogger(f"{fleet}.{name}")
        # propagate messages to fleet logger.

    logger.setLevel(level)
    handler = logging.FileHandler(logdir + f"/{fleet}/{name}.log")
    handler.setFormatter(FORMATTER)
    logger.addHandler(handler)
    loggers[name] = logger


def get_logger(name=None):
    if name not in loggers:
        return loggers["root"] if "root" in loggers else logging.getLogger()
    return loggers[name]
