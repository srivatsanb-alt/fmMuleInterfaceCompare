class MessageType:
    INIT = "init"
    REACHED = "reached"
    PERIPHERALS = "peripherals"
    SHERPA_STATUS = "sherpa_status"
    TRIP_STATUS = "trip_status"
    BOOKING = "book"
    PASS_TO_SHERPA = "pass_to_sherpa"
    RESOURCE_ACCESS = "resource_access"


class VisaType:
    PARKING = "parking"
    EXCLUSIVE_PARKING = "exclusive_parking"
    UNPARKING = "unparking"
    TRANSIT = "transit"


class VisaAccessType:
    REQUEST = "request"
    RELEASE = "release"
