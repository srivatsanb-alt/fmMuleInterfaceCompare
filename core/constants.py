class MessageType:
    INIT = "init"
    REACHED = "reached"
    PERIPHERALS = "peripherals"
    SHERPA_STATUS = "sherpa_status"
    TRIP_STATUS = "trip_status"
    BOOKING = "book"
    PASS_TO_SHERPA = "pass_to_sherpa"
    RESOURCE_ACCESS = "resource_access"
    DELETE_ONGOING_TRIP = "delete_ongoing_trip"
    INDUCT_SHERPA = "induct_sherpa"


class FleetStatus:
    STARTED = "started"
    STOPPED = "stopped"
    PAUSED = "paused"


class DisabledReason:
    EMERGENCY_STOP = "emergency_stop"
    STALE_HEARTBEAT = "stale_heartbeat"
