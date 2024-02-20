## Introduction ##

app/main.py is ASGI server implementation done using Fastapi and Uvicorn. App has multiple routers pertaining to different functions.

Each of the routers host multiple http, ws endpoints. The request body required for all of them have been defined in models/request_models.py using a python package called pydantic.


## Advantages of using Fastapi ##

1. More suited for backend compared to other packages(Flask, Django)
2. Fastapi provides docs pags, where the schema of requsets and response can be viewed, tested
3. Inbuilt Type validation

# Inbuilt validation ##
Fastapi raises HTTPException(status_code=422) if the incomming request body doesn't match the pre-defined pydantic model

## Routers ##

1.  [auth](routers/auth.py)
2.  [configure_fleet](routers/configure_fleet.py)
3.  [control_http](routers/control_http.py)
4.  [misc](routers/misc_http.py)
5.  [notifications](routers/notifications.py)
6.  [ota_update_http](routers/ota_update_http.py)
7.  [plugin_ws](routers/plugin_ws.py)
8.  [sherpa_http](routers/sherpa_http.py)
9.  [sherpa_ws](routers/sherpa_ws.py)
10. [station_http](routers/station_http.py)
11. [trips_http](routers/trips_http.py)
12. [updates_ws](routers/updates_ws.py)
13. [version_control](routers/version_control.py)


## Basic working ##

Any incomming request either gets processed directly inside the endpoint or gets passed to handler function([handlers/default/handlers.py](../handlers/default/handlers.py)). If the request is simply to fetch some data from the database, we would directly process the same get it done inside the endpoint block, but if something in the database has to be updated while processing the request we pass it on to the handlers.

To maintain the availability of the app and to preserve time order(process the requests in the same order in which they were received) we call the handler functions from the app using RQ(redis-queue). RQ is a FIFO job queue.


## App Security ##

1. When user login response is send with unique access_token and it is generated with an expiration time of one hour for each user ([generate_jwt_token](routers/dependencies.py#generate_jwt_token())).

2. We are generating API key of sherpa by appending a randomly generated 32-byte string to the Hardware ID ([gen_api_key](../utils/api_key_gen.py)).

## Custom Middleware ##

Custom middleware is to enhance the request-response cycle. It measures the processing time of each request and logs it. ([custom_fm_mw](main.py#@app.middleware("http")))

