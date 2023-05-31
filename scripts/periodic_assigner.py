import time
import logging

# ati code imports
from core.config import Config
from models.db_session import DBSession
from models.request_models import AssignNextTask
from models.fleet_models import SherpaStatus
from app.routers.dependencies import process_req
from models.trip_models import PendingTrip
from utils.util import check_if_timestamp_has_passed, str_to_dt


# adds scheduled trips to the job queue.


def enqueue_scheduled_trips(db_session: DBSession, schdeuled_job_id):
    pending_trips = db_session.session.query(PendingTrip).all()
    for pending_trip in pending_trips:
        if pending_trip.trip.scheduled:
            trip_metadata = pending_trip.trip.trip_metadata
            scheduled_start_time = str_to_dt(trip_metadata["scheduled_start_time"])
            if (
                not check_if_timestamp_has_passed(scheduled_start_time)
                and pending_trip.trip_id not in schdeuled_job_id
            ):
                assign_next_task_req = AssignNextTask()
                logging.getLogger().info(
                    f"will enqueue a job at {scheduled_start_time} for pending_trip with trip_id: {pending_trip.trip_id}"
                )

                process_req(None, assign_next_task_req, "self", dt=scheduled_start_time)
                schdeuled_job_id.append(pending_trip.trip_id)

    return schdeuled_job_id


# assigns next task to the sherpa.
def assign_next_task():
    rq_params = Config.get_fleet_rq_params()
    job_timeout = rq_params.get("generic_handler_job_timeout", 10)

    while True:
        schdeuled_job_id = []
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

                        # should not clog the generic handler
                        process_req(
                            None, assign_next_task_req, "self", ttl=int(0.5 * job_timeout)
                        )

                    schdeuled_job_id = enqueue_scheduled_trips(db_session, schdeuled_job_id)
                    time.sleep(2)

        except Exception as e:
            logging.getLogger().info(f"exception in periodic assigner script {e}")
            time.sleep(1)
