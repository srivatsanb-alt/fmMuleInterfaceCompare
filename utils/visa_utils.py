from models.db_session import session

from core.logs import get_logger
from models.fleet_models import Sherpa


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


def lock_linked_zones(zone_name, zone_type, sherpa_name):
    ezone = session.get_exclusion_zone(zone_name, zone_type)
    linked_gates = ezone.prev_linked_gates
    linked_gates.extend(ezone.next_linked_gates)
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


if __name__ == "__main__":
    pass
