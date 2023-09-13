class CONFIG_VIEW_PERMISSION_LEVELS:
    OPERATOR = 0
    SUPERVISOR = 1
    SUPPORT = 2


class CreateColKwargs:
    capped_default = {"capped": True, "max": 1, "size": 10}


class FrontendUsersValidator:
    user_details = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["name", "hashed_password", "role"],
            "properties": {
                "name": {"bsonType": "string", "description": "login username"},
                "hashed_password": {
                    "bsonType": "string",
                    "description": "Hashed login password",
                },
                "role": {
                    "bsonType": "string",
                    "enum": ["operator", "supervisor", "support"],
                    "description": "Role based access would be provided in the frontend app",
                },
            },
        }
    }


class PluginConfigValidator:
    plugin_info = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["plugin_ip", "plugin_port", "hashed_api_key"],
            "properties": {
                "hashed_api_key": {
                    "bsonType": "string",
                    "description": "plugin hashed_api_key",
                },
                "plugin_ip": {
                    "bsonType": "string",
                    "description": "plugin app IP",
                },
                "plugin_port": {
                    "bsonType": "string",
                    "description": "plugin app port",
                },
            },
        }
    }


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
            ],
            "properties": {
                "method": {
                    "bsonType": "string",
                    "enum": ["hungarian"],
                    "description": "Algorithm used to solve taxi dispatch problem",
                },
                "prioritise_waiting_stations": {
                    "bsonType": "bool",
                    "description": "If set to True, will multiply trip priority with a factor calculated based on wait time(time since booking)",
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
            },
        },
    }

    data_backup = {
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
                "sherpa_heartbeat_interval": {
                    "bsonType": "int",
                    "description": "sherpa will be considered disconnected, if no sherpa_status message was received in the last sherpa_heartbeat_interval seconds",
                    "minimum": 30,
                    "maximum": 90,
                }
            },
        }
    }

    rq = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["default_job_timeout", "generic_handler_job_timeout"],
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
                    "pattern": "^(\d{1,3}.\d{1,3}.\d{1,3}.\d{1,3})|(sanjaya.atimotors.com)$",
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
            "required": ["trip_types", "auto_park", "battery_swap"],
            "properties": {
                "trip_types": {
                    "bsonType": "array",
                    "description": "list of all the conditional_trips that needs to be activated`",
                },
                "auto_park": {
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
            ],
            "properties": {
                "simulate": {
                    "bsonType": "bool",
                    "description": "Whether to run fleet simulator or not, if set to true sherpa proxies will be created.",
                },
                "book_trips": {
                    "bsonType": "bool",
                    "description": "Whether to book predefined trips or not, trip definitions need to be configured in routes section",
                },
                "visa_handling": {
                    "bsonType": "bool",
                    "description": "Whether to simulate visas or not",
                },
                "speedup_factor": {
                    "bsonType": "double",
                    "description": "Run simulations at a accelarated pace by increasing the speedup_factor, speedup_factor=1.0 is real time",
                    "minimum": 1.0,
                },
                "average_velocity": {
                    "bsonType": "double",
                    "description": "Average velocity of sherpas to used in simulations",
                    "minimum": 0.1,
                    "maximum": 1.5,
                },
                "pause_at_station": {
                    "bsonType": "int",
                },
                "routes": {
                    "bsonType": "object",
                    "description": 'Add keys(key name can be anything) with values like [["Station A", "Station B"], ["10", "2023-05-31 15:00:00", "2023-05-31 16:00:00"]]',
                },
                "initialize_sherpas_at": {
                    "bsonType": "object",
                    "description": "Add sherpa name as key and station name as val",
                },
            },
        }
    }

    alerts = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": [
                "notifications",
                "slack_webhook_url",
            ],
            "properties": {
                "notifications": {
                    "bsonType": "bool",
                    "description": "Whether to send notifications/alert to the slack webhook",
                },
                "slack_webhook_url": {
                    "bsonType": "string",
                    "description": "slack slack webhook url",
                },
            },
        }
    }

    mule_config = {"$jsonSchema": {"bsonType": "object", "required": ["mule_site_config"]}}
    trip_metadata = {"$jsonSchema": {"bsonType": "object", "required": ["metadata"]}}


class ConfigDefaults:
    optimal_dispatch = {
        "method": "hungarian",
        "prioritise_waiting_stations": True,
        "eta_power_factor": 0.1,
        "priority_power_factor": 0.7,
        "max_trips_to_consider": 5,
    }
    data_backup = {"keep_size_mb": 1000}
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
        "trip_types": ["battery_swap", "auto_park"],
        "auto_park": {"book": True, "max_trips": 2, "threshold": 600, "priority": 1},
        "battery_swap": {"book": True, "max_trips": 2, "threshold": 15, "priority": 3},
    }
    simulator = {
        "simulate": False,
        "book_trips": False,
        "visa_handling": False,
        "speedup_factor": 1.01,
        "average_velocity": 0.8,
        "pause_at_station": 10,
        "initialize_sherpas_at": {},
        "routes": {},
    }
    alerts = {
        "notifications": True,
        "slack_webhook_url": "https://hooks.slack.com/services/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",
    }
    mule_config = {
        "mule_site_config": {
            "parent": "/app/mule/std_configs/site_configs/default_tug.toml",
            "control.policy": {"enforce_visa": False},
            "fleet": {
                "ws_url": "xyz",
                "fm_ip": "xyz",
                "data_url": "xyz",
                "api_key": "xyz",
                "chassis_number": "xyz",
            },
        }
    }
    trip_metadata = {"metadata": {"description": []}}


class DefaultFrontendUser:
    admin = {
        "name": "admin",
        "hashed_password": "03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4",
        "role": "support",
    }


class PluginConfigDefaults:
    plugin_info = {
        "plugin_ip": "plugin_alias",
        "plugin_port": "8002",
        "hashed_api_key": "a6a333480615e7339fbac0fa699559ce950a90df85d93a1f114a0c79dfc0750b",
    }
