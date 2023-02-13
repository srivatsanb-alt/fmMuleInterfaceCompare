import redis
import json
import os
import logging


def main():
    while True:
        redis_conn = redis.from_url(os.getenv("FM_REDIS_URI"))
        restart = False
        logging.getLogger().info("Will look for restart_fm key in redis")
        while not restart:
            restart = redis_conn.get("restart_fm")
            if restart is None:
                continue
            restart = json.loads(restart)
            if restart:
                logging.getLogger().info("Will restart fleet manager software")
                raise "Will restart fleet manager software"


if __name__ == "__main__":
    main()
