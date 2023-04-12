class MessageType:
    INIT = "init"
    REACHED = "reached"
    PERIPHERALS = "peripherals"
    SHERPA_STATUS = "sherpa_status"
    TRIP_STATUS = "trip_status"
    VERIFY_FLEET_FILES = "verify_fleet_files"
    BOOKING = "book"
    PASS_TO_SHERPA = "pass_to_sherpa"
    RESOURCE_ACCESS = "resource_access"
    DELETE_ONGOING_TRIP = "delete_ongoing_trip"
    DELETE_BOOKED_TRIP = "delete_booked_trip"
    INDUCT_SHERPA = "induct_sherpa"
    DELETE_VISA_ASSIGNMENTS = "delete_visa_assignments"
    DELETE_OPTIMAL_DISPATCH_ASSIGNMENTS = "delete_optimal_dispatch_assignments"
    ASSIGN_NEXT_TASK = "assign_next_task"
    FM_HEALTH_CHECK = "fm_health_check"
    SHERPA_ALERTS = "sherpa_alerts"


OptimalDispatchInfluencers = [
    MessageType.BOOKING,
    MessageType.DELETE_BOOKED_TRIP,
    MessageType.DELETE_ONGOING_TRIP,
    MessageType.INDUCT_SHERPA,
    MessageType.PASS_TO_SHERPA,
]

UpdateMsgs = [MessageType.SHERPA_STATUS, MessageType.TRIP_STATUS]

MAX_NUM_NOTIFICATIONS = 20
MAX_NUM_POP_UP_NOTIFICATIONS = 5


class FleetStatus:
    STARTED = "started"
    STOPPED = "stopped"
    PAUSED = "paused"


class DisabledReason:
    EMERGENCY_STOP = "emergency_stop"
    STALE_HEARTBEAT = "stale_heartbeat"
    SOFTWARE_NOT_COMPATIBLE = "software not compatible"
