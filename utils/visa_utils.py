import models.fleet_models as fm
import models.request_models as rqm
import models.visa_models as vm
from models.db_session import DBSession
from core.logs import get_logger


def get_reqd_zone_types(visa_type):
    reqd_zone_types = []
    if visa_type == rqm.VisaType.TRANSIT:
        reqd_zone_types.append(vm.ZoneType.LANE)

    elif visa_type == rqm.VisaType.PARKING:
        reqd_zone_types.append(vm.ZoneType.STAION)

    elif visa_type in {
        rqm.VisaType.EXCLUSIVE_PARKING,
        rqm.VisaType.UNPARKING,
        rqm.VisaType.SEZ,
    }:
        reqd_zone_types.append(vm.ZoneType.STATION)
        reqd_zone_types.append(vm.ZoneType.LANE)

    return reqd_zone_types


def get_linked_gates(ezone: vm.ExclusionZone):
    return ezone.prev_linked_gates + ezone.next_linked_gates


def split_zone_id(zone_id: str):
    return zone_id.rsplit("_", 1)


def lock_exclusion_zone(ezone: vm.ExclusionZone, sherpa: fm.Sherpa, exclusive: bool = True):
    if len(ezone.sherpas) == 0:
        ezone.sherpas = []

    ezone.sherpas.append(sherpa)
    ezone.exlusive = exclusive


def can_lock_exclusion_zone(
    dbsession: DBSession,
    ezone: vm.ExclusionZone,
    sherpa: fm.Sherpa,
    zone_id: str,
    zone_name: str,
    zone_type: str,
    exclusive: bool = True,
):
    reason = None
    if ezone is None:
        reason = f"Unable to get a ezone with zone_id: {zone_id}"
        get_logger("visa").error(reason)
        return False, reason

    get_logger("visa").info(
        f"{ezone.zone_id} access held by {[s.name for s in ezone.sherpas]}"
    )

    if len(ezone.sherpas) == 0:
        reason = f"{sherpa.name} granted lock for {zone_id} exclusive={exclusive}"
        get_logger("visa").info(reason)
        return True, reason

    if sherpa in ezone.sherpas and len(ezone.sherpas) == 1:
        reason = f"{sherpa.name} already granted lock for {zone_id} exclusive={exclusive}"
        get_logger("visa").info(reason)
        return True, reason

    if ezone.exclusivity:
        reason = f"{sherpa.name} denied lock for {zone_id} exclusive access held by {[s.name for s in ezone.sherpas]}"
        get_logger("visa").info(reason)
        return False, reason

    elif not exclusive:
        reason = f"{sherpa.name} granted lock for {zone_id} ezone held by sherpas {[s.name for s in ezone.sherpas]} without exclusivity"
        get_logger("visa").info(reason)
        return True, reason
    else:
        reason = f"exlusive access to {zone_id} can't be granted already held by sherpas {[s.name for s in ezone.sherpas]}"
        get_logger("visa").info(reason)
        return False, reason


def unlock_exclusion_zone(dbsession: DBSession, ezone: vm.ExclusionZone, sherpa: fm.Sherpa):

    reason = None
    if ezone is None:
        reason = f"Unable to get a ezone with zone_id: {ezone.zone_id}"
        get_logger("visa").error(reason)
        return False, reason

    if sherpa not in ezone.sherpas:
        reason = f"{sherpa.name} doesn't hold {ezone.zone_id}"
        get_logger("visa").warning(reason)
        return False, reason

    ezone.sherpas.remove(sherpa)
    if len(ezone.sherpas) == 0:
        ezone.exclusivity = None

    reason = f"{sherpa.name} doesn't hold {ezone.zone_id} anymore"
    get_logger("visa").info(reason)
    return True, reason


def can_grant_visa(
    dbsession: DBSession, sherpa: fm.Sherpa, req: rqm.VisaReq, exclusive: bool = True
):
    visa_type = req.visa_type
    zone_name = req.zone_name
    reqd_zone_types = get_reqd_zone_types(visa_type)

    reqd_ezones = []
    all_lzs = []

    # check for specific visa
    for reqd_zone_type in reqd_zone_types:
        zone_type = reqd_zone_type
        ezone = dbsession.get_exclusion_zone(zone_name, zone_type)
        for ez in get_linked_gates(ezone):
            all_lzs.append(ez)
        granted, reason = can_lock_exclusion_zone(
            dbsession, ezone, sherpa, ezone.zone_id, zone_name, zone_type, exclusive
        )
        if not granted:
            return granted, reason, []

        reqd_ezones.append(ezone)

    # check for linked gates
    for reqd_zone_type in reqd_zone_types:
        for lz in all_lzs:
            lz_zone_name, lz_zone_type = split_zone_id(lz.zone_id)
            granted, reason = can_lock_exclusion_zone(
                dbsession,
                lz,
                sherpa,
                lz.zone_id,
                lz_zone_name,
                lz_zone_type,
                exclusive,
            )
            if not granted:
                return granted, reason, []

    reason = "all visas reqd are available"
    return True, reason, reqd_ezones


def get_visas_to_release(dbsession: DBSession, sherpa: fm.Sherpa, req: rqm):

    visa_type = req.visa_type
    zone_name = req.zone_name
    visas_to_release = []

    reqd_zone_types = get_reqd_zone_types(visa_type)
    for reqd_zone_type in reqd_zone_types:
        zone_type = reqd_zone_type
        ezone = dbsession.get_exclusion_zone(zone_name, zone_type)
        visas_to_release.append(ezone)

    return visas_to_release
