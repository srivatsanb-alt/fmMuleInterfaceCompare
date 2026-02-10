import logging
import os
from multiprocessing import Process
import json
import redis
import time

# ati code imports
import utils.rq_utils as rqu
from scripts.periodic_updates import send_periodic_updates
from scripts.periodic_backup import backup_data
from scripts.periodic_assigner import assign_next_task
from scripts.periodic_fm_health_check import periodic_health_check
from scripts.periodic_misc_processes import misc_processes
from scripts.alerts import send_slack_alerts
from scripts.conditional_trips import book_conditional_trips
from scripts.fm_errors_check import periodic_error_check
from optimal_dispatch.router import start_router_module
from master_fm_comms.send_updates_to_mfm import send_mfm_updates
from master_fm_comms.send_ws_updates_to_mfm import send_ws_msgs_to_mfm


func_handles = {
    "send_periodic_updates": send_periodic_updates,
    "assign_next_task": assign_next_task,
    "periodic_health_check": periodic_health_check,
    "backup_data": backup_data,
    "send_slack_alerts": send_slack_alerts,
    "send_mfm_updates": send_mfm_updates,
    "send_ws_msgs_to_mfm": send_ws_msgs_to_mfm,
    "misc_processes": misc_processes,
    "book_conditional_trips": book_conditional_trips,
    "start_router_module": start_router_module,
    "periodic_error_check": periodic_error_check,
}


class FMProcessesHandler:
    def __init__(self):
        self.all_processes = []

    def start_all_processes(self):
        for proc_name, proc_handle in func_handles.items():
            proc = Process(target=proc_handle, name=proc_name)
            try:
                proc.start()
                logging.info(f"Started process: {proc.name}")
            except Exception as e:
                logging.info(f"Couldn't start process: {proc.name}, Exception: {e}")
            self.all_processes.append(proc)

    def restart_process(self, proc):
        self.all_processes.remove(proc)
        new_proc = Process(target=func_handles[proc.name], name=proc.name)
        new_proc.start()
        self.all_processes.append(new_proc)

    def monitor_processes(self):
        while True:
            for proc in self.all_processes:
                if proc.is_alive():
                    continue

                if proc.exitcode == 0:
                    continue

                logging.info(f"{proc.name} ended with exitcode: {proc.exitcode}")

            time.sleep(5)


if __name__ == "__main__":
    redis_conn = redis.from_url(os.getenv("FM_REDIS_URI"))
    if os.getenv("FM_DEV_LOCAL", None) == "true":
        import fm_init
        fm_init.main()
        redis_conn.flushall()
    logging.info(f"all queues {rqu.Queues.get_queues()}")

    for q in rqu.Queues.get_queues():
        process = Process(target=rqu.start_worker, args=(q,))
        process.start()

    fm_processes_handler = FMProcessesHandler()
    fm_processes_handler.start_all_processes()

    redis_conn.set("is_fleet_manager_up", json.dumps(True))
    logging.info("Ati Fleet Manager started")
    FM_TAG = os.getenv("FM_TAG")
    logging.info(f"fm software tag: {FM_TAG}")

    fm_processes_handler.monitor_processes()
