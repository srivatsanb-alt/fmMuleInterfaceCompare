optimal_dispatch_validator = {
    "$jsonSchema": {
        "bsonType": "object",
        "required": [
            "type",
            "method",
            "prioritise_waiting_stations",
            "eta_power_factor",
            "priority_power_factor",
            "max_trips_to_consider",
        ],
        "properties": {
            "type": {
                "bsonType": "string",
            },
            "method": {
                "bsonType": "string",
            },
            "prioritise_waiting_stations": {
                "bsonType": "string",
            },
            "eta_power_factor": {
                "bsonType": "string",
            },
        },
    },
}
