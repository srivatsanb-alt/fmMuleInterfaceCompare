from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .routers import sherpa_http, sherpa_ws, trips_http, auth, updates
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
