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
                    "minimum": 100,
                    "description": "Will try make sure disk space used by static/data_backup folder size(MB) is less than keep_size_mb",
                }
            },
        },
    }
    comms = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": [
                "sherpa_heartbeat_interval",
            ],
            "properties": {
                "mule_heartbeat_interval": {
                    "bsonType": "int",
                    "description": "sherpa will be considered disconnected, if no sherpa_status message was received in the last sherpa_heartbeat_interval seconds",
                }
            },
        }
    }

    rq = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["default_job_timeout", "generic_handler_job_timeou"],
            "properties": {
                "default_job_timeout": {
                    "bsonType": "int",
                    "description": "Jobs/requests queued up in any redis queue will timeout after default_job_timeout seconds",
                    "minimum": 10,
                    "maximum": 50,
                },
                "generic_handler_job_timeout": {
                    "bsonType": "int",
                    "minimum": 10,
                    "maximum": 50,
                    "description": "Jobs/requests queued up in any redis queue will timeout after generic_handler_job_timeout seconds",
                },
            },
        }
    }

    stations = {
        "$jsonSchema": {
            "bsonType": "object",
            "properties": {
                "dispatch_timeout": {
                    "bsonType": "int",
                    "description": "if sherpa reaches a station dispath optional station, sherpa would move after dispatch_timeout seconds even if dispatch button is not pressed",
                    "minimum": 1,
                }
            },
        }
    }

    plugins = {
        "$jsonSchema": {
            "bsonType": "object",
            "properties": {
                "all_plugins": {
                    "bsonType": "array",
                    "enum": ["conveyor", "summon_button", "ies"],
                    "description": "list of all the plugins that needs to be activated`",
                }
            },
        }
    }

    master_fm = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": [
                "mfm_ip",
                "mfm_port",
                "mfm_cert_file",
                "ws_scheme",
                "http_scheme",
                "ws_suffix",
                "send_updates",
                "ws_update_freq",
                "update_freq",
                "api_key",
            ],
            "properties": {
                "mfm_ip": {
                    "bsonType": "string",
                    "enum": ["sanjaya.atimotors.com", "localhost"],
                    "description": "domain name or ip for accessing sanjaya/master_fm",
                },
                "mfm_port": {
                    "bsonType": "string",
                    "enum": ["443", "9010"],
                    "description": "Port through which sanjaya/master_fm server can be accessed",
                },
                "mfm_cert_file": {
                    "bsonType": "string",
                    "enum": ["/etc/ssl/certs/ca-certificates.crt"],
                    "description": "Path to ssl cert file to use to access sanjaya/master_fm",
                },
                "ws_scheme": {
                    "bsonType": "string",
                    "enum": ["ws", "wss"],
                    "description": "Websocket protocol to use, use wss if mfm_port is set to 443 else use ws",
                },
                "http_scheme": {
                    "bsonType": "string",
                    "enum": ["http", "https"],
                    "description": "Http protocol to use, use https if mfm_port is set to 443 else use http",
                },
                "ws_suffix": {
                    "bsonType": "string",
                    "enum": ["ws/api/v1/master_fm/fm_client"],
                    "description": "ws url suffix",
                },
                "send_updates": {
                    "bsonType": "bool",
                    "description": "paramater is used to decide if updates needs to be sent to sanjaya/master_fm server",
                },
                "ws_update_freq": {
                    "bsonType": "int",
                    "description": "Will send live updates every ws_update_freq seconds",
                },
                "update_freq": {
                    "bsonType": "int",
                    "description": "Will send event-driven updates every update_freq seconds",
                },
                "api_key": {
                    "bsonType": "string",
                    "description": "Api_key required to connect to master_fm/sanjaya server",
                },
            },
        }
    }

    conditional_trips = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["trip_types", "idling_sherpas", "battery_swap"],
            "properties": {
                "trip_types": {
                    "bsonType": "array",
                    "enum": ["idling_sherpas", "battery_swap"],
                    "description": "list of all the conditional_trips that needs to be activated`",
                },
                "idling_sherpas": {
                    "bsonType": "object",
                    "required": ["book", "max_trips", "threshold", "priority"],
                    "properties": {
                        "book": {
                            "bsonType": "bool",
                            "description": "Whether to book trip to parking area for sherpas that are idling",
                        },
                        "max_trips": {
                            "bsonType": "int",
                            "description": "Max number of sherpas that can be booked with trips to parking simultaneously",
                            "minimum": 1,
                        },
                        "threshold": {
                            "bsonType": "int",
                            "description": "Threshold in seconds to wait before booking a trip to parking area for a sherpa",
                            "minimum": 60,
                        },
                        "priority": {
                            "bsonType": "int",
                            "description": "Set trip priority for the booking",
                            "minimum": 1,
                            "maximum": 3,
                        },
                    },
                },
                "battery_swap": {
                    "bsonType": "object",
                    "required": ["book", "max_trips", "threshold", "priority"],
                    "properties": {
                        "book": {
                            "bsonType": "bool",
                            "description": "Whether to book trip to battery swap/charging area for sherpas whose battery level is lesser than threshold",
                        },
                        "max_trips": {
                            "bsonType": "int",
                            "description": "Max number of sherpas that can be booked with trips to battery swap/charging area simultaneously",
                            "minimum": 1,
                        },
                        "threshold": {
                            "bsonType": "int",
                            "description": "Trip will be booked to battery swap/charging area if battery level is below the threshold",
                            "minimum": 5,
                            "maximum": 25,
                        },
                        "priority": {
                            "bsonType": "int",
                            "description": "Set trip priority for the booking",
                            "minimum": 1,
                            "maximum": 10,
                        },
                    },
                },
            },
        }
    }

    users = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["name", "hashed_password", "role"],
            "properties": {
                "name": {"bsonType": "string", "description": "login username"},
                "hashed_password": {
                    "bsonType": "string",
                    "description": "hashed login password",
                },
                "role": {
                    "bsonType": "string",
                    "enum": ["operator", "supervisor", "support"],
                    "description": "Role based access would be provided in the frontend app",
                },
            },
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
    comms = {"sherpa_heartbeat_interval": 60}
    rq = {"default_job_timeout": 15, "generic_handler_job_timeout": 10}
    stations = {"dispatch_timeout": 10}
    master_fm = {
        "mfm_ip": "sanjaya.atimotors.com",
        "mfm_port": "443",
        "mfm_cert_file": "/etc/ssl/certs/ca-certificates.crt",
        "http_scheme": "https",
        "ws_scheme": "wss",
        "ws_suffix": "ws/api/v1/master_fm/fm_client",
        "send_updates": False,
        "ws_update_freq": 60,
        "update_freq": 120,
        "api_key": "",
    }
    conditional_trips = {
        "trip_types": ["battery_swap", "idling_sherpas"],
        "idling_sherpas": {"book": False, "max_trips": 2, "threshold": 600, "priority": 1},
        "battery_swap": {"book": False, "max_trips": 2, "threshold": 15, "priority": 3},
    }
    plugins = {"all_plugins": []}
