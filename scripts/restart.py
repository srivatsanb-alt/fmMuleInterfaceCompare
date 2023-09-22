import redis
import json
import os
import time
import logging


def main():
    redis_conn = redis.from_url(os.getenv("FM_REDIS_URI"))
    redis_conn.set("restart_fm", json.dumps(False))
    restart = False
    logging.getLogger().info("Will look for restart_fm key in redis")
    while not restart:
        restart = redis_conn.get("restart_fm")
        if restart is None:
            continue
        restart = json.loads(restart)
        if restart:
            logging.getLogger().info("Will restart fleet manager software")
            os.system("docker restart fm_plugins")
            raise Exception("Will restart fleet manager software")

        time.sleep(5e-1)


if __name__ == "__main__":
    main()
