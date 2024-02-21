## Introduction ##

FM backend is an ASGI RESPI Implementation using [FastAPI](https://fastapi.tiangolo.com/) 

[app/main.py](main.py) is the REST API ASGI server implementation. FastAPI app has multiple routers pertaining to different functions. Each of the routers host multiple http, ws endpoints. 

REST API is stateless, all the states gets stored in the database


## Advantages of using FastAPI ##

1. FastApi is more suited, faster for backend application compared to other packages(Flask, Django)

2. FastApi provides inbuilt documentaion tested, All the request/response models,schema can be viewed at 
```
http://<fm_ip>:8001/docs
```

3. [Inbuilt Type validation](#inbuilt-type-validation)


## Inbuilt type validation ##

Fastapi raises HTTPException(status_code=422) if the incomming request body doesn't match the pre-defined pydantic model

The request body required for all of the endpoints have been defined in [request_models](../models/request_models.py).


## Routers ##

Listing important endpoints hosted by each of the routers

1.  [auth](routers/auth.py)
```
    - Login
    - Add/Edit user credentials
    - Delete user
```

2.  [configure_fleet](routers/configure_fleet.py)
```
    - Add/Edit/Delete fleet
    - Add/Edit/Delete sherpa
    - Update map files of a fleet
```

3.  [control_http](routers/control_http.py)
```
    - Start/stop fleet operation
    - emergency stop all the sherpas in fleet
    - emergency stop sherpa 
```

4.  [misc](routers/misc_http.py)
```
    - Get site info 
    - Get master fleet data
```

5.  [notifications](routers/notifications.py)
```
    - Notification websocket endpoint - Where one would get new notifications periodically 
    - clear notification using notification_id
    - clear all notifications pertaining to certatin log_level(info, alert, action_request) 
```

6.  [ota_update_http](routers/ota_update_http.py)
```
    - Get FM updates available in master_fm server 
    - Download a certain FM update available in master_fm server 
```

7.  [plugin_ws](routers/plugin_ws.py)
```
    - Websocket endpoint to send/receive message to/from fm_plugins application 
```

8.  [sherpa_http](routers/sherpa_http.py)
```
    - Receive reached msg from sherpa
    - Receive visa/resource request from sherpa
    - Receive peripheral update from sherpa ( sherpa has unhitched trolley, moved totes to conveyor)
    - Check software compatibility
```

9.  [sherpa_ws](routers/sherpa_ws.py)
```
    - Websocket endpoint to send/receive message to/from sherpas
```

10. [station_http](routers/station_http.py)
```
    - Enable/disable a station
    - Get basic info about the station
```

11. [trips_http](routers/trips_http.py)
```
    - Book a trip
    - Delete a booked trip
    - Delete a ongoing trip
```

12. [updates_ws](routers/updates_ws.py)
```
    - Websocket endpoint in which periodic updates regarding the whole fleet.

    The update would have details about all the sherpas(initialised, trip_id, disabled etc), fleets(status - started, stopped, maintenance etc)
```

13. [version_control](routers/version_control.py)
```
    - Add compatible sherpa version
    - Delete compatible sherpa version
```

## Basic working ##

All the request being sent to FM is to either fetch some data from database or to update some details to the database

If the request is simply to fetch some data from the database, for instance a request to get status of a trip, we would directly process the same inside the endpoint block, but if we want to do some CRUD operation on the database, for instance booking a new trip(insert), we pass it on to the job queue.

To maintain the availability of the app and to preserve time order(process the requests in the same order in which they were received) we use job queue .

To get more details on how we interact with database check [Interaction with DB]

## Queuing a job ## 

We use the package RQ (https://python-rq.org/) for job queue

We queue a job along with the handler function Handlers.handle ([handlers/default/handlers.py](../handlers/default/handlers.py)). This Handlers.handle call the approiate method based the type of the request. 

Any request which being queued should have an attribute "type". All the message types have been defined [core.constants](../core/constants.py)

```
handle_reached(req) if req.type == "reached"
handle_book(req) if req.type == "book"
```

We add the following kwargs to ensure smooth working of the job queue. 

```
job_timeout - If the time taken by the handler is greater than the job_timeout, RQ timeout is raised. 

ttl - if client send ttl, we add it to the job kwargs

retry - Retry multiple time on failure
```

To get more details which job goes to which queue, check [FM job queues]


## App Security ##

All fm users(dashboard, plugins) except by sherpa etc have to pass the [access_token](#access-token) in the request header for the request to be accepted

The sherpas have to pass [api_key](#api-key) in the request header for the request to be accepted

## Access token ##

Access token is jwt token(https://jwt.io/) 

Basically jwt token have attributes called signature and secret. Jwt token is created by encoding signature with the secret, similarly one can decode the token to obtain the signature. 

In our case jwt signature is the username. 

Secret remains constant for an entire FM session(until FM restart). This secret is set in environment variable FM_SECRET_TOKEN during the course of FM bring up [set_token.py](../scripts/set_token.py)

When a user shares access_token in the request header, backend would be able to decode the signature from access_token, thereby getting know which user who sent the request.


## How do users get access token ## 

Access token is shared to the user in the response to the login endpoint [Auth](routers/auth.py)


## API key ## 

API key is a randomly generated string  

To make it human recognizable we append hardware_id of the component(sherpa, conveyor) etc to the randomly generated string

Please check [gen_api_key](../utils/api_key_gen.py).


## Custom Middleware ##

We have a [custom_fm_mw](main.py#@app.middleware("http")) to do basic thing like add process times to the response header. It can expanded to do multiple things in future

All the responses will have a attribute X-Process-Time in the header which is time the FM backend took to process the paritcular request

This is also logged in process_times.log


## User Credentials ##

All the user credentials are stored in mongo db. 

In [FM init](../fm_init.py) we make sure that default user "admin" is always present. 
check the method maybe_add_default_admin_user in [db_utils](../utils/db_utils.py)
