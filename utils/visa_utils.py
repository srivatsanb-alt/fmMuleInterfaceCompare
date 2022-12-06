from typing import List
from models.db_session import session

from core.logs import get_logger
from models.fleet_models import Sherpa
from models.request_models import VisaType
from models.visa_models import ExclusionZone


def lock_exclusion_zone(zone_name, zone_type, sherpa_name, exclusive=True, test=False):
    zone_id = f"{zone_name}_{zone_type}"
    sherpa: Sherpa = session.get_sherpa(sherpa_name)
    ezone = session.get_exclusion_zone(zone_name, zone_type)
    if not ezone:
        get_logger(sherpa.name).error(
            f"no such zone: zone_name={zone_name}, zone_type={zone_type}"
        )
        return False

    get_logger(sherpa.name).info(
        f"{zone_id} access held by {[s.name for s in ezone.sherpas]}"
    )

    if len(ezone.sherpas) == 0:
        # no other sherpa in ezone
        get_logger(sherpa.name).info(
            f"{sherpa.name} granted lock for {zone_id},exclusive={exclusive},test={test} "
        )
        if not test:
            ezone.sherpas = [sherpa]
            ezone.exclusivity = exclusive
        return True

    if len(ezone.sherpas) == 1 and ezone.sherpas[0] == sherpa:
        # sherpa already has access
        get_logger(sherpa.name).info(
            f"{sherpa.name} granted lock for {zone_id},exclusive={exclusive},test={test}"
        )
        if not test:
            ezone.exclusivity = exclusive
        return True

    if ezone.exclusivity:
        # ezone already locked exclusively by another sherpa.
        get_logger(sherpa.name).info(
            f"{sherpa.name} denied lock for {zone_id}, exclusive access held by {ezone.sherpas[0]},test={test}"
        )
        return False
    elif not exclusive:
        # can't lock exclusively since there are other sherpas in ezone.
        get_logger(sherpa.name).info(
            f"{sherpa.name} granted lock for {zone_id},exclusive={exclusive},test={test}"
        )
        if not test and sherpa not in ezone.sherpas:
            ezone.sherpas.append(sherpa)
        return True
    else:
        get_logger(sherpa.name).info(
            f"{sherpa.name} denied exclusive lock for {zone_id},test={test}"
        )
        return False


def get_linked_gates(ezone: ExclusionZone):
    return ezone.prev_linked_gates + ezone.next_linked_gates


def split_zone_id(zone_id: str):
    return zone_id.rsplit("_", 1)


def can_lock_linked_zones(zone_name, zone_type, sherpa_name):
    ezone = session.get_exclusion_zone(zone_name, zone_type)
    linked_gates: List[ExclusionZone] = get_linked_gates(ezone)
    can_lock_linked_gates: List[bool] = []

    for lz in linked_gates:
        lz_name, lz_type = split_zone_id(lz.zone_id)
        can_lock = lock_exclusion_zone(lz_name, lz_type, sherpa_name, test=True)
        can_lock_linked_gates.append(can_lock)

    return all(can_lock_linked_gates)


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
        zone_name, zone_type = split_zone_id(ezone.zone_id)
        unlock_exclusion_zone(zone_name, zone_type, sherpa_name)


def maybe_grant_visa(zone_name, visa_type, sherpa_name):
    ezone = session.get_exclusion_zone(zone_name, "lane")
    linked_zones = get_linked_gates(ezone) if ezone else []

    linked_zone_flag = True

    if visa_type == VisaType.PARKING:
        if len(linked_zones):
            linked_zone_flag = can_lock_linked_zones(zone_name, "station", sherpa_name)
        return lock_exclusion_zone(zone_name, "station", sherpa_name) and linked_zone_flag

    if visa_type in [VisaType.EXCLUSIVE_PARKING, VisaType.UNPARKING, VisaType.SEZ]:
        if len(linked_zones):
            linked_zone_flag = can_lock_linked_zones(
                zone_name, "station", sherpa_name
            ) and can_lock_linked_zones(zone_name, "lane", sherpa_name)
        return (
            lock_exclusion_zone(zone_name, "station", sherpa_name)
            and lock_exclusion_zone(zone_name, "lane", sherpa_name)
            and linked_zone_flag
        )

    if visa_type == VisaType.TRANSIT:
        if len(linked_zones):
            linked_zone_flag = can_lock_linked_zones(zone_name, "lane", sherpa_name)
        return lock_exclusion_zone(zone_name, "lane", sherpa_name) and linked_zone_flag


if __name__ == "__main__":
    pass
