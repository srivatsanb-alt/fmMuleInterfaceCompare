from models.db_session import DBSession
from models.request_models import AssignNextTask
from models.fleet_models import SherpaStatus
from app.routers.dependencies import process_req
from models.trip_models import PendingTrip
from utils.util import check_if_timestamp_has_passed
import time
import logging

# adds scheduled trips to the job queue.


def enqueue_scheduled_trips(db_session: DBSession, schdeuled_job_id):
    pending_trips = db_session.session.query(PendingTrip).all()
    for pending_trip in pending_trips:
        if pending_trip.trip.scheduled:
            if (
                not check_if_timestamp_has_passed(pending_trip.trip.start_time)
                and pending_trip.trip_id not in schdeuled_job_id
            ):
                assign_next_task_req = AssignNextTask()
                logging.getLogger().info(
                    f"will enqueue a job at {pending_trip.trip.start_time} for pending_trip with trip_id: {pending_trip.trip_id}"
                )

                process_req(
                    None, assign_next_task_req, "self", dt=pending_trip.trip.start_time
                )
                schdeuled_job_id.append(pending_trip.trip_id)

    return schdeuled_job_id


# assigns next task to the sherpa.
def assign_next_task():
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
                        process_req(None, assign_next_task_req, "self", ttl=3)

                    schdeuled_job_id = enqueue_scheduled_trips(db_session, schdeuled_job_id)
                    time.sleep(2)

        except Exception as e:
            logging.getLogger().info(f"exception in periodic assigner script {e}")
            time.sleep(1)
