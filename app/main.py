from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .routers import sherpa_http, sherpa_ws, trips_http, auth, updates, misc_http, control_http
import logging


logging.basicConfig(
    format="{asctime} {levelname} [{funcName}] {message}",
    style="{",
    level=logging.INFO,
)
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/api/static", StaticFiles(directory="static"), name="static")

app.include_router(sherpa_http.router)
app.include_router(sherpa_ws.router)
app.include_router(trips_http.router)
app.include_router(updates.router)
app.include_router(auth.router)
app.include_router(misc_http.router)
app.include_router(control_http.router)
