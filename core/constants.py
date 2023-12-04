class MessageType:
    INIT = "init"
    REACHED = "reached"
    PERIPHERALS = "peripherals"
    SHERPA_STATUS = "sherpa_status"
    FLEET_START_STOP = "fleet_start_stop"
    TRIP_STATUS = "trip_status"
    BOOKING = "book"
    PASS_TO_SHERPA = "pass_to_sherpa"
    RESOURCE_ACCESS = "resource_access"
    DELETE_ONGOING_TRIP = "delete_ongoing_trip"
    DELETE_BOOKED_TRIP = "delete_booked_trip"
    INDUCT_SHERPA = "induct_sherpa"
    ASSIGN_NEXT_TASK = "assign_next_task"
    FM_HEALTH_CHECK = "fm_health_check"
    SHERPA_ALERTS = "sherpa_alerts"
    MISC_PROCESS = "misc_process"
    FORCE_DELETE_ONGOING_TRIP = "force_delete_ongoing_trip"
    SAVE_ROUTE = "save_route"
    TRIGGER_OPTIMAL_DISPATCH = "trigger_optimal_dispatch"


OptimalDispatchInfluencers = [
    MessageType.BOOKING,
    MessageType.DELETE_BOOKED_TRIP,
    MessageType.DELETE_ONGOING_TRIP,
    MessageType.INDUCT_SHERPA,
    MessageType.PASS_TO_SHERPA,
    MessageType.FLEET_START_STOP,
]

UpdateMsgs = [MessageType.SHERPA_STATUS, MessageType.TRIP_STATUS]

MAX_NUM_NOTIFICATIONS = 20
MAX_NUM_POP_UP_NOTIFICATIONS = 5


class FleetStatus:
    STARTED = "started"
    STOPPED = "stopped"
    PAUSED = "paused"
    MAINTENANCE = "maintenance"


class DisabledReason:
    EMERGENCY_STOP = "emergency_stop"
    STALE_HEARTBEAT = "stale_heartbeat"
    SOFTWARE_NOT_COMPATIBLE = "software not compatible"
