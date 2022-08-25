from models.db_session import session

from core.logs import get_logger
from models.fleet_models import Sherpa


def lock_exclusion_zone(zone_id, zone_type, sherpa_name, exclusive=True):
    sherpa: Sherpa = session.get_sherpa(sherpa_name)
    ezone = session.get_exclusion_zone(zone_id, zone_type)
    if not ezone:
        get_logger(sherpa.name).error(
            f"no such zone: zone_id={zone_id}, zone_type={zone_type}"
        )
    id_type = f"{ezone.zone_id}_{ezone.zone_type}"

    if len(ezone.sherpas) == 0:
        # no other sherpa in ezone
        get_logger(sherpa.name).info(
            f"{sherpa.name} granted lock for {id_type},exclusive={exclusive} "
        )
        ezone.sherpas = [sherpa]
        ezone.exclusivity = exclusive
        return True

    if len(ezone.sherpas) == 1 and ezone.sherpas[0] == sherpa:
        # sherpa already has access
        get_logger(sherpa.name).info(
            f"{sherpa.name} granted lock for {id_type},exclusive={exclusive} "
        )
        ezone.exclusivity = exclusive
        return True

    if ezone.exclusivity:
        # ezone already locked exclusively by another sherpa.
        get_logger(sherpa.name).info(
            f"{sherpa.name} denied lock for {id_type}, exclusive access held by {ezone.sherpas[0]}"
        )
        return False
    elif not exclusive:
        # can't lock exclusively since there are other sherpas in ezone.
        get_logger(sherpa.name).info(
            f"{sherpa.name} granted lock for {id_type},exclusive={exclusive}"
        )
        if sherpa not in ezone.sherpas:
            ezone.sherpas.append(sherpa)
        return True
    else:
        get_logger(sherpa.name).info(f"{sherpa.name} denied exclusive lock for {id_type}")
        return False


def unlock_exclusion_zone(zone_id, zone_type, sherpa_name):
    sherpa: Sherpa = session.get_sherpa(sherpa_name)
    ezone = session.get_exclusion_zone(zone_id, zone_type)
    id_type = f"{ezone.zone_id}_{ezone.zone_type}"

    if sherpa not in ezone.sherpas:
        get_logger(sherpa.name).info(
            f"can't unlock {id_type} for {sherpa.name}, not locked by it"
        )
        return False
    ezone.sherpas.remove(sherpa)
    if len(ezone.sherpas) == 0:
        ezone.exclusivity = None
    get_logger(sherpa.name).info(f"unlocked {id_type} for {sherpa.name} ")
    return True


def clear_all_locks(sherpa_name):
    sherpa: Sherpa = session.get_sherpa(sherpa_name)
    for ezone in sherpa.exclusion_zones:
        unlock_exclusion_zone(ezone.zone_id, ezone.zone_type, sherpa_name)


if __name__ == "__main__":
    pass
