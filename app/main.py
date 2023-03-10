import time
import uvicorn
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles


# ati code imports
from app.routers import (
    sherpa_http,
    sherpa_ws,
    trips_http,
    auth,
    updates_ws,
    misc_http,
    control_http,
    station_http,
    notifications,
    configure_fleet,
)

# for easy maintainance and usability of the app, we use routers
# each functionality can be separately implemented on router rather than modifying the
# entire app.

# setup logging
# log_conf_path = os.path.join(os.getenv("FM_CONFIG_DIR"), "logging.conf")
# logging.config.fileConfig(log_conf_path)

# create FastAPI object
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Process-Time"],
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


app.include_router(sherpa_http.router)
app.include_router(sherpa_ws.router)
app.include_router(trips_http.router)
app.include_router(updates_ws.router)
app.include_router(auth.router)
app.include_router(misc_http.router)
app.include_router(control_http.router)
app.include_router(station_http.router)
app.include_router(notifications.router)
app.include_router(configure_fleet.router)


def get_uvicorn_config():
    uvi_config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=int(os.getenv("FM_PORT")),
        log_level="info",
        log_config=os.path.join(os.getenv("FM_CONFIG_DIR"), "logging.conf"),
        reload=True,
    )
    return uvi_config


def main():
    app.mount("/api/static", StaticFiles(directory="/app/static"), name="static")
    config = get_uvicorn_config()
    server = uvicorn.Server(config)
    server.run()


if __name__ == "__main__":
    main()
