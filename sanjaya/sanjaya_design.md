# Request Response models for Sanjaya app #

## Auth ## 
1. Login
```markdown
from: ui
to: sanjaya-backend

POST /api/v1/auth/user_login
Request:
{
    name: str 
    password: str
}
Response:
{
}
```

## User Actions - Through UI ##
1. Add a new client
```markdown
from: ui
to: sanjaya-backend

POST /api/v1/add/fm_client
Request:
{
    customer_name: str (Bosch/TVS/Forvia)
    description: str, (TVS 3 wheeler plant, Hosur/Bosch NNpura, Bgl)
    timezone: str (Asia/Kolkata)
}
Response:
{
    client_id: int,
    api_key: str 
}
```

2. Update software for a client 
```markdown
from: ui
to: sanjaya-backend

POST /api/v1/update/version
Request:
{
    client_id: int,
    fm_version: float,
    mule_version: float
}
Response:
{}
```

3. Update default software versions
```markdown
from: ui
to: sanjaya-backend

POST /api/v1/update/default/version
Request:
{
    fm_version: float,
    mule_version: float
}
Response:
{}
```

4. Add version
```markdown
from: ui
to: sanjaya-backend

GET /api/v1/version/{mule/fm}/{version}
Request: 
{}
Response:
{}
```

5. Remove version
```markdown
from: ui
to: sanjaya-backend

DELETE /api/v1/version/{mule/fm}/{version}
Request: 
{}
Response:
{}
```

6. Get all supported versions
```markdown
from: ui
to: sanjaya-backend

GET /api/v1/get_supported_versions
Request: 
{}
Response:
{
    fm: List[float]
    mule: List[float]
}
```

## Updates from FM clients - Websockets/https ##

1. Site info update

```markdown
trigger: FM restart
from: FM-client 
to: sanjaya-backend

Request:
POST /api/v1/client_update/{client_id}/site_info
{
    "fleet_names": List[str],
    "timezone": str,
    "software_fm_version": float,
    "software_mule_version": float, 
}

Response:
{}
```
   
2. Master data update
```markdown
trigger: FM restart
from: FM-client 
to: sanjaya-backend

Request:
POST /api/v1/client_update/{client_id}/master_data/{fleet_name}
{
    sherpa_names: List[str]
    gmaj: dict
}

Response:
{}
```

3. Fleet status message
```markdown
trigger: every 30 seconds 
from: FM-client 
to: sanjaya-backend

WS /ws/api/v1/client_update/fleet_status

json:
{
    fleet_name: "hall3"
    fleet_status: "started"
    FK-S16: {
             pose: List[floot]
             mode: str            
             error: null
             battery_level: int
             disabled: bool
             disabled_reason: str
            }
    }

```

4. Trip update - Sent when a trip ends/fails
```markdown
trigger: when a trip  ends 
from: FM-client 
to: sanjaya-backend

POST /api/v1/client_update/{client_id}/trip_analytics
Request:
{
    <trip_id>: {
        "trip_id": 1,
        "sherpa_name": "FK-S16",
        "fleet_name": "hall3",
        "trip_details": {
        "status": "cancelled",
        "etas_at_start": [
            26.275,
            23.287
        ],
        "etas": [
            0,
            0
        ],
        "trip_leg_id": null,
        "next_idx_aug": null,
        "trip_leg_from_station": null,
        "trip_leg_to_station": null,
        "trip_metadata": {
            "scheduled": "False",
            "description": ""
        },
        "route": [
            "station 0",
            "station 1"
        ],
        "priority": 1,
        "scheduled": false,
        "time_period": 0,
        "booking_id": 1,
        "booking_time": "2023-02-14 13:26:54",
        "start_time": "2023-02-14 13:26:57",
        "end_time": "2023-02-14 13:40:12",
        "updated_at": "2023-02-14 13:40:12"
        }
    }
}

Response: 
{}
```

5. Trip Analytics update - Sent when a trip leg is ends
```markdown
trigger: when a trip leg ends 
from: FM-client 
to: sanjaya-backend

POST /api/v1/client_update/{client_id}/trip_analytics
{
    <trip_leg_id>: {
        "sherpa_name": "FK-S16",
        "trip_id": 184,
        "trip_leg_id": 233,
        "start_time": "2023-02-15 15:25:29",
        "end_time": "2023-02-15 15:26:02",
        "from_station": null,
        "to_station": "station 0",
        "cte": 0,
        "te": 0,
        "expected_trip_time": 26.275,
        "actual_trip_time": 32,
        "time_elapsed_obstacle_stoppages": 0,
        "time_elapsed_visa_stoppages": 0,
        "time_elapsed_other_stoppages": 0,
        "num_trip_msg": 31,
        "created_at": "2023-02-15 15:25:30",
        "updated_at": "2023-02-15 15:26:02"
  }
}
```


# PSQL tables Sanjaya app #

1. FMClient
```markdown
id : int
customer_name: str
description: str
timezone: str
api_key: str
fm_version: float
mule_version: float
```

2. DefaultSoftwareVersions
```markdown
fm_version: int
mule_version: int
```

3. Fleets
```markdown
id: int (index)
name: str 
client_id: int (ForeignKey FMClient)
gmaj: jsonb
```

4. Sherpas
```markdown
id: int 
name: str 
fleet_name: int (ForeignKey Fleets)
```

4. SherpaStatus
```markdown
sherpa_name: str
mode: str
pose: List[floot]
error: str/null
battery_level: int
disabled: bool
disabled_reason: str
```

5. Trips:
```markdown
id = Column(Integer, primary_key=True, index=True)
booking_id = Column(Integer, index=True)
sherpa doing the trip
sherpa_name = Column(String, index=True)
fleet_name = Column(String, index=True)
booking_time = Column(DateTime)
start_time = Column(DateTime, index=True)
end_time = Column(DateTime, index=True)
route = Column(ARRAY(String))
augmented_route = Column(ARRAY(String))
aug_idxs_booked = Column(ARRAY(Integer))
status = Column(String, index=True)
etas_at_start = Column(ARRAY(Float))
etas = Column(ARRAY(Float))
scheduled = Column(Boolean, index=True)
time_period = Column(Integer)
priority = Column(Float)
trip_metadata = Column(JSONB)
other_info = Column(JSONB)
```

6. TripAnalytics
```markdown
sherpa_name = Column(String, index=True)
trip_id = Column(Integer, index=True)
trip_leg_id = Column(Integer, primary_key=True, index=True)
start_time = Column(DateTime, index=True)
end_time = Column(DateTime, index=True)
from_station = Column(String, index=True)
to_station = Column(String, index=True)
cte = Column(Float)
te = Column(Float)
expected_trip_time = Column(Float)
actual_trip_time = Column(Float)
time_elapsed_obstacle_stoppages = Column(Float)
time_elapsed_visa_stoppages = Column(Float)
time_elapsed_other_stoppages = Column(Float)
num_trip_msg = Column(Integer)
```






