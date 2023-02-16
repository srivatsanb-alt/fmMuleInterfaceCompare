import time
import logging
import logging.config
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .routers import (
    manage_multi_fm_http,
)

# for easy maintainance and usability of the app, we use routers
# each functionality can be separately implemented on router rather than modifying the
# entire app.

# setup logging
log_conf_path = "/app/misc/logging.conf"
logging.config.fileConfig(log_conf_path)

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


# app.mount("/api/static", StaticFiles(directory="/app/static"), name="static")
app.include_router(manage_multi_fm_http.router)
