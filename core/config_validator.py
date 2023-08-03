class ConfigValidator:
    optimal_dispatch = {
        "$jsonSchema": {
            "type": "object",
            "required": [
                "method",
                "prioritise_waiting_stations",
                "eta_power_factor",
                "priority_power_factor",
                "max_trips_to_consider",
                "permission_level",
            ],
            "properties": {
                "method": {"type": "string", "enum": ["hungarian"]},
                "prioritise_waiting_stations": {
                    "type": "boolean",
                },
                "eta_power_factor": {"type": "number", "minimum": 0.1, "maximum": 1.0},
                "priority_power_factor": {
                    "type": "number",
                    "minimum": 0.1,
                    "maximum": 1.0,
                },
                "max_trips_to_consider": {
                    "type": "number",
                    "minimum": 1,
                    "maximum": 20,
                },
                "permission_level": {"type": "number", "minimum": 1, "maximum": 3},
            },
        },
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
