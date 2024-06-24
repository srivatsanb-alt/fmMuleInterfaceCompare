import secrets
import redis
import os

from models.mongo_client import FMMongo

def main():
    token = secrets.token_urlsafe(32)
    try:
        with FMMongo() as fm_mongo:
            app_security_params = fm_mongo.get_document_from_fm_config("app_security")        
        if app_security_params.get("secret_token"):
            token = app_security_params.get("secret_token")
    except:
        pass 
    with redis.from_url(os.getenv("FM_REDIS_URI")) as redis_conn:
        redis_conn.set("FM_SECRET_TOKEN", token)
    print(f"Set FM_SECRET_TOKEN")

if __name__ == "__main__":
    main()
