import time
import logging
from sqlalchemy.sql import not_


# ati code imports
from models.mongo_client import FMMongo
from models.db_session import DBSession
import models.request_models as rqm
from models.fleet_models import SherpaStatus
from app.routers.dependencies import process_req
from models.trip_models import PendingTrip
from utils.util import check_if_timestamp_has_passed, str_to_dt, report_error, proc_retry


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
                trigger_optimal_dispatch_req = rqm.TriggerOptimalDispatch(
                    fleet_name=pending_trip.trip.fleet_name
                )
                logging.getLogger().info(
                    f"will enqueue a job at {scheduled_start_time} for pending_trip with trip_id: {pending_trip.trip_id}"
                )

                process_req(
                    None,
                    trigger_optimal_dispatch_req,
                    "self",
                    redis_conn=None,
                    dt=scheduled_start_time,
                )
                schdeuled_job_id.append(pending_trip.trip_id)

    return schdeuled_job_id


# assigns next task to the sherpa.
@proc_retry(times=50)
@report_error
def assign_next_task():
    with FMMongo() as fm_mongo:
        rq_params = fm_mongo.get_document_from_fm_config("rq")

    job_timeout = rq_params["generic_handler_job_timeout"]

    schdeuled_job_id = []
    logging.getLogger().info("starting periodic assigner script")
    with DBSession() as db_session:
        while True:
            all_sherpa_status = (
                db_session.session.query(SherpaStatus)
                .filter(SherpaStatus.assign_next_task.is_(True))
                .filter(not_(SherpaStatus.disabled.is_(True)))
                .all()
            )
            for sherpa_status in all_sherpa_status:
                logging.getLogger("status_updates").info(
                    f"will send assign task request for {sherpa_status.sherpa_name}"
                )

                # should not clog the generic handler
                assign_next_task_req = rqm.AssignNextTask(
                    sherpa_name=sherpa_status.sherpa_name,
                    ttl=int(0.5 * job_timeout),
                )

                process_req(None, assign_next_task_req, "self")

            schdeuled_job_id = enqueue_scheduled_trips(db_session, schdeuled_job_id)
            db_session.session.expire_all()
            time.sleep(2)
