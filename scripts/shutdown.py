import os
import redis
from rq.command import send_shutdown_command
from rq.worker import Worker

redis_conn = redis.from_url(os.getenv("FM_REDIS_URI"))

workers = Worker.all(redis_conn)
for worker in workers:
    send_shutdown_command(redis_conn, worker.name)
