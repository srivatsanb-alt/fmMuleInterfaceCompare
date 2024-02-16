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

1.  auth
2.  configure_fleet
3.  control_http
4.  misc
5.  notifications
6.  ota_update_http
7.  plugin_ws
8.  sherpa_http
9.  sherpa_ws
10. station_http
11. trips_http
12. updates_ws
13. version_control


## Basic working ##

Any incomming request either gets processed directly inside the endpoint or gets passed to handler function(handlers/default/handlers.py). If the request is simply to fetch some data from the database, we would directly process the same get it done inside the endpoint block, but if something in the database has to be updated while processing the request we pass it on to the handlers.

To maintain the availability of the app and to preserve time order(process the requests in the same order in which they were received) we call the handler functions from the app using RQ(redis-queue). RQ is a FIFO job queue.
