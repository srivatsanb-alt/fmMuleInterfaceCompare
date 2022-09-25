import time
from utils.rq import Queues, enqueue
from core.config import Config
from models.request_models import SherpaStatusMsg
import sys
import json
import os
import uvicorn
from models.db_session import session
from multiprocessing import Process
import redis
from models.fleet_models import Sherpa


class FleetSimulator:
    def __init__(self):
        self.handler_obj = Config.get_handler()
        self.sherpa_apps = []

    def handle(self, handler, msg):
        handler.handle(msg)

    def host_uvicorn(self, config):

        server = uvicorn.Server(config)
        server.run()

    def host_all_mule_app(self):
        self.kill_all_mule_app()
        all_sherpas = session.get_all_sherpas()

        sys.path.append(os.environ["MULE_ROOT"])
        os.environ["ATI_SUB"] = "ipc:////app/out/zmq_sub"
        os.environ["ATI_PUB"] = "ipc:////app/out/zmq_sub"
        redis_db = redis.from_url(os.getenv("FM_REDIS_URI"))
        redis_db.set("control_init", json.loads(True))
        from mule.ati.fastapi.mule_app import mule_app

        port = 5001
        for sherpa in all_sherpas:
            config = uvicorn.Config(mule_app, host="0.0.0.0", port=port, reload=True)
            sherpa.ip_address = "0.0.0.0"
            sherpa.port = str(port)
            self.sherpa_apps.append(
                Process(target=self.host_uvicorn, args=[config], daemon=True)
            )
            self.sherpa_apps[-1].start()
            port = port + 1

        session.close()

    def kill_all_mule_app(self):
        all_sherpas = session.get_all_sherpas()
        for sherpa in all_sherpas:
            sherpa.port = None
        for proc in self.sherpa_apps:
            proc.kill()

    def send_sherpa_status(self, sherpa_name, mode=None, pose=None, battery_status=None):
        sherpa: Sherpa = session.get_sherpa(sherpa_name)
        msg = {}
        msg["type"] = "sherpa_status"
        msg["source"] = sherpa_name
        msg["sherpa_name"] = sherpa_name
        msg["timestamp"] = time.time()
        msg["mode"] = "fleet" if not mode else mode
        msg["current_pose"] = sherpa.status.pose if not pose else pose
        msg["battery_status"] = -1 if not battery_status else battery_status
        print(f"will send a proxy sherpa status {msg}")

        if msg["type"] == "sherpa_status":
            msg = SherpaStatusMsg.from_dict(msg)
            enqueue(Queues.handler_queue, self.handle, self.handler_obj, msg, ttl=1)
