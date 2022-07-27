import logging
import os

from db import session_maker
from models.fleet_models import Fleet, Sherpa

FORMATTER = logging.Formatter("%(asctime)s %(levelname)s [%(funcName)s] %(message)s")


def init_logging():
    logdir = os.environ["HIVEMIND_LOG_DIR"]
    try:
        os.mkdir(logdir)
    except FileExistsError:
        pass
    setup_root_logger(logdir)
    with session_maker() as db:
        db_fleets = db.query(Fleet).all()
    for fleet in db_fleets:
        init_logging_for_fleet(fleet, logdir)


def init_logging_for_fleet(fleet: Fleet, logdir):
    fleet_name = fleet.name
    fleet_id = fleet.id
    try:
        os.mkdir(logdir + "/" + fleet_name)
    except FileExistsError:
        pass

    # set up fleet-level logger.
    setup_logger(fleet_name, logdir)
    with session_maker() as db:
        db_sherpas = db.query(Sherpa).filter(Sherpa.fleet_id == fleet_id).all()
        for sherpa in db_sherpas:
            # set up sherpa-level logger.
            setup_logger(fleet_name, logdir, sherpa.name)


def setup_root_logger(logdir, level=logging.INFO):
    logger = logging.getLogger()
    logger.setLevel(level)
    logger.handlers.clear()
    handler = logging.FileHandler(logdir + "/fleet_manager.log")
    handler.setFormatter(FORMATTER)
    logger.addHandler(handler)


def setup_logger(fleet: str, logdir, name="fleet", level=logging.INFO):
    handler = logging.FileHandler(logdir + f"/{fleet}/{name}.log")
    handler.setFormatter(FORMATTER)
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
