from typing import List
from models.db_session import session

from core.logs import get_logger
from models.fleet_models import Sherpa
from models.request_models import VisaType
from models.visa_models import ExclusionZone


def lock_exclusion_zone(zone_name, zone_type, sherpa_name, exclusive=True, actual=True):
    zone_id = f"{zone_name}_{zone_type}"
    sherpa: Sherpa = session.get_sherpa(sherpa_name)
    ezone = session.get_exclusion_zone(zone_name, zone_type)
    if not ezone:
        get_logger(sherpa.name).error(
            f"no such zone: zone_name={zone_name}, zone_type={zone_type}"
        )
        return False

    if len(ezone.sherpas) == 0:
        # no other sherpa in ezone
        get_logger(sherpa.name).info(
            f"{sherpa.name} granted lock for {zone_id},exclusive={exclusive} "
        )
        if actual:
            ezone.sherpas = [sherpa]
            ezone.exclusivity = exclusive
        return True

    if len(ezone.sherpas) == 1 and ezone.sherpas[0] == sherpa:
        # sherpa already has access
        get_logger(sherpa.name).info(
            f"{sherpa.name} granted lock for {zone_id},exclusive={exclusive} "
        )
        if actual:
            ezone.exclusivity = exclusive
        return True

    if ezone.exclusivity:
        # ezone already locked exclusively by another sherpa.
        get_logger(sherpa.name).info(
            f"{sherpa.name} denied lock for {zone_id}, exclusive access held by {ezone.sherpas[0]}"
        )
        return False
    elif not exclusive:
        # can't lock exclusively since there are other sherpas in ezone.
        get_logger(sherpa.name).info(
            f"{sherpa.name} granted lock for {zone_id},exclusive={exclusive}"
        )
        if actual and sherpa not in ezone.sherpas:
            ezone.sherpas.append(sherpa)
        return True
    else:
        get_logger(sherpa.name).info(f"{sherpa.name} denied exclusive lock for {zone_id}")
        return False


def get_linked_gates(ezone):
    linked_gates = ezone.prev_linked_gates
    linked_gates.extend(ezone.next_linked_gates)

    return linked_gates


def lock_linked_zones(zone_name, zone_type, sherpa_name):
    ezone = session.get_exclusion_zone(zone_name, zone_type)
    linked_gates = get_linked_gates(ezone)
    can_lock_linked_gates = []
    for lz in linked_gates:
        lz_name, lz_type = lz.zone_id.split("_")
        can_lock = lock_exclusion_zone(lz_name, lz_type, sherpa_name, actual=False)
        can_lock_linked_gates.append(can_lock)

    if all(can_lock_linked_gates):
        return lock_exclusion_zone(zone_name, zone_type, sherpa_name, exclusive=False)
    else:
        return False


def unlock_exclusion_zone(zone_name, zone_type, sherpa_name):
    zone_id = f"{zone_name}_{zone_type}"
    sherpa: Sherpa = session.get_sherpa(sherpa_name)
    ezone = session.get_exclusion_zone(zone_name, zone_type)

    if not ezone:
        get_logger(sherpa.name).error(
            f"no such zone: zone_name={zone_name}, zone_type={zone_type}"
        )
        return False

    if sherpa not in ezone.sherpas:
        get_logger(sherpa.name).info(
            f"can't unlock {zone_id} for {sherpa.name}, not locked by it"
        )
        return False
    ezone.sherpas.remove(sherpa)
    if len(ezone.sherpas) == 0:
        ezone.exclusivity = None
    get_logger(sherpa.name).info(f"unlocked {zone_id} for {sherpa.name} ")
    return True


def clear_all_locks(sherpa_name):
    sherpa: Sherpa = session.get_sherpa(sherpa_name)
    for ezone in sherpa.exclusion_zones:
        zone_name, zone_type = ezone.zone_id.split("_")
        unlock_exclusion_zone(zone_name, zone_type, sherpa_name)


def maybe_grant_visa(zone_name, visa_type, sherpa_name):
    zone_id = f"{zone_name}_{visa_type}"
    sherpa: Sherpa = session.get_sherpa(sherpa_name)

    ezone = session.get_exclusion_zone(zone_name, "lane")

    other_zones: List[ExclusionZone] = sherpa.exclusion_zones
    linked_zones = get_linked_gates(ezone)

    if len(other_zones) > 1 or (len(other_zones) > 0 and other_zones[0] != ezone):
        visa_str = f"Foreign policy violation - sherpa {sherpa_name} asking for visa to zone {zone_id} while holding visa for other_zones"
        get_logger(sherpa_name).warn(visa_str)
        return False

    if len(linked_zones) > 0:
        if visa_type != VisaType.TRANSIT:
            visa_str = f"sherpa {sherpa_name} asking for non-transit visa_type {visa_type} at intersection-zone {zone_id}. Rejecting visa."
            get_logger(sherpa_name).warn(visa_str)
            return False
        else:
            return lock_linked_zones(zone_name, "lane", sherpa_name)

    if visa_type == VisaType.PARKING:
        return lock_exclusion_zone(zone_name, "station", sherpa_name)

    if visa_type in {VisaType.EXCLUSIVE_PARKING, VisaType.UNPARKING}:
        return lock_exclusion_zone(
            zone_name, "station", sherpa_name
        ) and lock_exclusion_zone(zone_name, "lane", sherpa_name)

    if visa_type == VisaType.TRANSIT:
        return lock_exclusion_zone(zone_name, "lane", sherpa_name)


if __name__ == "__main__":
    pass
