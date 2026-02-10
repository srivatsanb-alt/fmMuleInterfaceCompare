import time
import uvicorn
import os
import aioredis
import logging
import logging.config

from fastapi_limiter import FastAPILimiter
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

import io
import zipfile
import tempfile
from fastapi.responses import FileResponse

load_dotenv()

import sys
sys.path.append(os.path.join(os.getcwd()))

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
    version_control,
    plugin_ws,
    ota_update_http,
    super_user_http,
    staging_area,
)
import utils.log_utils as lu

# get log config
logging.config.dictConfig(lu.get_log_config_dict())

# for easy maintainance and usability of the app, we use routers
# each functionality can be separately implemented on router rather than modifying the
# entire app.

# setup logging
# log_conf_path = os.path.join(os.getenv("FM_MISC_DIR"), "logging.conf")
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


@app.on_event("startup")
async def startup():
    redis_db = aioredis.from_url(
        os.getenv("FM_REDIS_URI"), encoding="utf-8", decode_responses=True
    )
    await FastAPILimiter.init(redis_db)


@app.middleware("http")
async def custom_fm_mw(request: Request, call_next):
    start_time = time.time()

    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    logging.getLogger("process_times").info(
        f"Process time - url: {request.url}: {round(process_time*1000, 2)} ms"
    )
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
app.include_router(version_control.router)
app.include_router(plugin_ws.router)
app.include_router(ota_update_http.router)
app.include_router(super_user_http.router)
app.include_router(staging_area.router)


def get_uvicorn_config():
    uvi_config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=int(os.getenv("FM_PORT")),
        log_level="info",
        log_config=logging.config.dictConfig(lu.get_log_config_dict()),
        reload=True,
    )
    return uvi_config

root_dir =  "" if os.getenv("FM_INSTALL_DIR") == "/" else os.getenv("FM_INSTALL_DIR")

from fastapi import Depends, HTTPException
from utils.auth_utils import AuthValidator, DualAuthValidator
from fastapi.responses import FileResponse

# Custom static file handlers with dual authentication
@app.get("/api/static/{file_path:path}")
async def serve_static_file(
    file_path: str, 
    user=Depends(DualAuthValidator('fm'))
):
    """Serve static files with dual authentication (Bearer token or Basic Auth)"""
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    static_dir = os.path.join(root_dir, "static")
    file_location = os.path.join(static_dir, file_path)
    
    if not os.path.exists(file_location) or not os.path.isfile(file_location):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(file_location)

@app.get("/api/downloads/{file_path:path}")
async def serve_downloads_file(
    file_path: str, 
    user=Depends(DualAuthValidator('fm'))
):
    """Serve download files with dual authentication (Bearer token or Basic Auth)"""
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    downloads_dir = os.path.join(root_dir, "downloads")
    file_location = os.path.join(downloads_dir, file_path)
    
    if not os.path.exists(file_location) or not os.path.isfile(file_location):
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(file_location)


@app.get("/api/map/download/{map_name}")
async def download_map_folder(map_name: str, user=Depends(AuthValidator)):
    """Download all files under static/<map_name>/map as a zip archive."""
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    map_folder = os.path.join(root_dir, "static", map_name, "map")
    if not (os.path.isdir(map_folder)):
        raise HTTPException(status_code=404, detail="Map folder not found")

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(map_folder):
            for f in files:
                zf.write(os.path.join(root, f), os.path.relpath(os.path.join(root, f), map_folder))
    zip_buffer.seek(0)

    filename = f"{map_name}_map.zip"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}

    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
        tmp.write(zip_buffer.getvalue())
        tmp_path = tmp.name

    class TempFileResponse(FileResponse):
        async def __call__(self, scope, receive, send):
            try:
                await super().__call__(scope, receive, send)
            finally:
                try: os.remove(self.path)
                except Exception: pass

    return TempFileResponse(tmp_path, media_type="application/zip", headers=headers, filename=filename)

def main():
    config = get_uvicorn_config()
    server = uvicorn.Server(config)
    print("====================API Server Started and can be accessed at====================")
    print(f"http://localhost:{config.port}/docs")
    server.run()


if __name__ == "__main__":
    main()
