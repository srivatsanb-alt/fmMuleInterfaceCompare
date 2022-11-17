from models.db_session import DBSession
from models.request_models import AssignNextTask
from models.fleet_models import SherpaStatus
from app.routers.dependencies import process_req
import time
import logging


def assign_next_task():
    while True:
        sleep_time = 20
        logging.getLogger().info(f"Will Wait for {sleep_time} seconds for the DB to be up")
        time.sleep(sleep_time)
        try:
            logging.getLogger().info("starting periodic assigner script")
            with DBSession() as db_session:
                while True:
                    all_sherpa_status = (
                        db_session.session.query(SherpaStatus)
                        .filter(SherpaStatus.assign_next_task.is_(True))
                        .all()
                    )
                    for sherpa_status in all_sherpa_status:
                        logging.getLogger("status_updates").info(
                            f"will send assign task request for {sherpa_status.sherpa_name}"
                        )
                        assign_next_task_req = AssignNextTask(
                            sherpa_name=sherpa_status.sherpa_name
                        )

                        process_req(None, assign_next_task_req, "self")

                    time.sleep(2)

        except Exception as e:
            logging.getLogger().info(f"exception in periodic assigner script {e}")
            time.sleep(1)
