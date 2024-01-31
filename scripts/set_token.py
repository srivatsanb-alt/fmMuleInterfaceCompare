import secrets
import redis
import os


def main():
    token = secrets.token_urlsafe(32)
    # redis_conn = redis.from_url(os.getenv("FM_REDIS_URI"))
    with redis.from_url(os.getenv("FM_REDIS_URI")) as redis_conn:
        redis_conn.set("FM_SECRET_TOKEN", token)
    print(f"Set FM_SECRET_TOKEN")


if __name__ == "__main__":
    main()
