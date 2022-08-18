from redis import Redis
from rq.command import send_shutdown_command
from rq.worker import Worker

redis = Redis()

workers = Worker.all(redis)
for worker in workers:
    send_shutdown_command(redis, worker.name)
