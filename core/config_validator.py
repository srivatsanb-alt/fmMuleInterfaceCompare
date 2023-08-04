class ConfigValidator:
    optimal_dispatch = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": [
                "method",
                "prioritise_waiting_stations",
                "eta_power_factor",
                "priority_power_factor",
                "max_trips_to_consider",
                "permission_level",
            ],
            "properties": {
                "method": {
                    "bsonType": "string",
                    "enum": ["hungarian"],
                    "description": "Algorithm used to solve taxi dispatch problem",
                },
                "prioritise_waiting_stations": {
                    "bsonType": "bool",
                    "description": "If set to True, multiply trip priority with a factor calculated based on wait time(time since booking)",
                },
                "eta_power_factor": {
                    "bsonType": "double",
                    "minimum": 0.1,
                    "maximum": 1.0,
                    "description": "Modifier - actual eta will be modified to eta^eta_power_factor",
                },
                "priority_power_factor": {
                    "bsonType": "double",
                    "minimum": 0.1,
                    "maximum": 1.0,
                    "description": "Modifier - actual trip priority will be modified to trip_priority^priority_power_factor",
                },
                "max_trips_to_consider": {
                    "bsonType": "int",
                    "minimum": 1,
                    "maximum": 20,
                    "description": "Max number of trips that will be considered for optimal dispatch, decrease to lessen conputational cost",
                },
                "permission_level": {
                    "bsonType": "int",
                    "minimum": 1,
                    "maximum": 3,
                    "description": "For role based access",
                },
            },
        },
    }

    backup = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": [
                "keep_size_mb",
            ],
            "properties": {
                "keep_size_mb": {
                    "bsonType": "int",
                    "description": "will make sure disk space used by static/data_backup folder size(MB) is less than keep_size_mb",
                }
            },
        },
    }
    comms = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": [
                "mule_heartbeat_interval",
            ],
            "properties": {
                "mule_heartbeat_interval": {
                    "bsonType": "int",
                    "description": "mule will be considered disconnected, if no sherpa_status message was received in the last mule_heartbeat_interval seconds",
                }
            },
        }
    }

    simulator = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": [
                "simulate",
                "book_trips",
                "visa_handling",
                "speedup_factor",
                "average_velocity",
                "pause_at_station",
                "conveyor_capacity",
            ],
        }
    }


class ConfigDefaults:
    optimal_dispatch = {
        "method": "hungarian",
        "prioritise_waiting_stations": True,
        "eta_power_factor": 0.1,
        "priority_power_factor": 0.7,
        "max_trips_to_consider": 5,
        "permission_level": 1,
    }
    backup = {"keep_size_mb": 1000}
    comms = {"mule_heartbeat_interval": 60}
    simulator = {
        "simulate": False,
        "book_trips": False,
        "visa_handling": False,
        "speedup_factor": 1.0,
        "average_velocity": 0.8,
        "pause_at_station": 10.0,
        "conveyor_capacity": 6,
    }
