import logging
import os
from multiprocessing import Process
import json
import redis

# ati code imports
import utils.rq_utils as rqu
from scripts.periodic_updates import send_periodic_updates
from scripts.periodic_backup import backup_data
from scripts.periodic_assigner import assign_next_task
from scripts.periodic_fm_health_check import periodic_health_check
from scripts.periodic_misc_processes import misc_processes
from scripts.alerts import send_slack_alerts
from scripts.conditional_trips import book_conditional_trips
from master_fm_comms.send_updates_to_mfm import send_mfm_updates
from master_fm_comms.send_ws_updates_to_mfm import send_ws_msgs_to_mfm


if __name__ == "__main__":
    redis_conn = redis.from_url(os.getenv("FM_REDIS_URI"))

    logging.info(f"all queues {rqu.Queues.get_queues()}")

    for q in rqu.Queues.get_queues():
        process = Process(target=rqu.start_worker, args=(q,))
        process.start()

    # send periodic status update
    Process(target=send_periodic_updates).start()

    # start periodic assigner scripts
    Process(target=assign_next_task).start()

    # start periodic fm health check
    Process(target=periodic_health_check).start()

    # start backup data
    Process(target=backup_data).start()

    # start send slack alerts script
    Process(target=send_slack_alerts).start()

    # start mfm update script
    Process(target=send_mfm_updates).start()
    Process(target=send_ws_msgs_to_mfm).start()

    # start misc processes
    Process(target=misc_processes).start()

    # start book conditonal trips script
    Process(target=book_conditional_trips).start()

    redis_conn.set("is_fleet_manager_up", json.dumps(True))
    logging.info("Ati Fleet Manager started")

    FM_TAG = os.getenv("FM_TAG")
    logging.info(f"fm software tag: {FM_TAG}")
