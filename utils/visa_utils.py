import logging
import logging.config

# ati code imports
import models.fleet_models as fm
import models.request_models as rqm
import models.visa_models as vm
from models.db_session import DBSession

import utils.log_utils as lu

# get log config
logging.config.dictConfig(lu.get_log_config_dict())


def get_reqd_zone_types(visa_type):
    reqd_zone_types = []

    if visa_type == rqm.VisaType.TRANSIT:
        reqd_zone_types.append(vm.ZoneType.LANE)

    elif visa_type == rqm.VisaType.PARKING:
        reqd_zone_types.append(vm.ZoneType.STATION)

    elif visa_type == rqm.VisaType.UNPARKING:
        reqd_zone_types.append(vm.ZoneType.STATION)
        reqd_zone_types.append(vm.ZoneType.LANE)

    else:
        raise ValueError(f"{visa_type} not supported")

    return reqd_zone_types


def get_reqd_zone_ids(zone_name, reqd_zone_types):
    reqd_zone_ids = []

    for zone_type in reqd_zone_types:
        reqd_zone_ids.append(f"{zone_name}_{zone_type}")

    return reqd_zone_ids


def get_linked_gates(ezone: vm.ExclusionZone):
    return ezone.prev_linked_gates + ezone.next_linked_gates


def split_zone_id(zone_id: str):
    return zone_id.rsplit("_", 1)


def lock_exclusion_zone(ezone: vm.ExclusionZone, sherpa: fm.Sherpa, exclusive: bool = True):
    if len(ezone.sherpas) == 0:
        ezone.sherpas = []

    ezone.sherpas.append(sherpa)


def can_lock_exclusion_zone(
    dbsession: DBSession,
    ezone: vm.ExclusionZone,
    sherpa: fm.Sherpa,
    exclusive: bool = True,
):
    zone_id = ezone.zone_id
    reason = None

    logging.getLogger("visa").info(
        f"{ezone.zone_id} access held by {[s.name for s in ezone.sherpas]}"
    )

    if len(ezone.sherpas) == 0:
        reason = f"{sherpa.name} can be granted lock for {zone_id} exclusive={exclusive}"
        logging.getLogger("visa").info(reason)
        return True, reason

    if sherpa in ezone.sherpas and len(ezone.sherpas) == 1:
        reason = f"{sherpa.name} already has {zone_id} exclusive={exclusive}"
        logging.getLogger("visa").info(reason)
        return True, reason

    if ezone.exclusivity:
        reason = f"{sherpa.name} cannot be granted {zone_id} exclusive access held by {[s.name for s in ezone.sherpas]}"
        logging.getLogger("visa").info(reason)
        return False, reason

    elif not exclusive:
        reason = f"{sherpa.name} can be granted {zone_id} without exclusivity, ezone held by sherpas {[s.name for s in ezone.sherpas]}"
        logging.getLogger("visa").info(reason)
        return True, reason
    else:
        reason = f"exlusive access to {zone_id} can't be granted already held by sherpas {[s.name for s in ezone.sherpas]}"
        logging.getLogger("visa").info(reason)
        return False, reason


def unlock_exclusion_zone(dbsession: DBSession, ezone: vm.ExclusionZone, sherpa: fm.Sherpa):

    reason = None
    if ezone is None:
        reason = f"Unable to get a ezone but will still accept release request"
        logging.getLogger("visa").error(reason)
        return False, reason

    if sherpa not in ezone.sherpas:
        reason = f"{sherpa.name} doesn't hold {ezone.zone_id} but will still accept release request"
        logging.getLogger("visa").warning(reason)
        return False, reason

    ezone.sherpas.remove(sherpa)

    reason = f"{sherpa.name} doesn't hold {ezone.zone_id} anymore, visa release done"
    logging.getLogger("visa").info(reason)
    return True, reason


def can_grant_visa(
    dbsession: DBSession, sherpa: fm.Sherpa, req: rqm.VisaReq, exclusive: bool = True
):
    visa_type = req.visa_type
    zone_name = req.zone_name
    reqd_zone_types = get_reqd_zone_types(visa_type)
    reqd_zone_ids = get_reqd_zone_ids(zone_name, reqd_zone_types)
    unavailable_ezs = dbsession.get_unavailable_reqd_ezones(reqd_zone_ids)

    """
        ### Checking unavailable visas for two reasons ###

        1. Sherpa asking for the ez might be already holding it
        2. Non exclusive access can be granted

    """

    for ezone in unavailable_ezs:
        exclusive = ezone.exclusivity
        zone_name = ezone.zone_id
        granted, reason = can_lock_exclusion_zone(dbsession, ezone, sherpa, exclusive)
        if not granted:
            return granted, reason, []

    reqd_ezones = dbsession.get_reqd_ezones(reqd_zone_ids)
    if len(reqd_zone_ids) != len(reqd_ezones):
        available_zone_ids = [ezone.zone_id for ezone in reqd_ezones]
        raise ValueError(
            f"Couldn't get details of all the required ezones. reqd: {reqd_zone_ids}, available: {available_zone_ids}"
        )

    ## get all the linked ezones ###
    linked_ezs = []
    unavailable_linked_ezs = []
    for ez in reqd_ezones:
        linked_ezs.extend(get_linked_gates(ez))

    linked_ezs = set(linked_ezs)

    ## get all the linked gate and unavailable ezones ###
    if len(linked_ezs) > 0:
        all_locked_ezones = dbsession.get_all_locked_ezones()
        unavailable_linked_ezs = [
            linked_ez for linked_ez in linked_ezs if linked_ez in all_locked_ezones
        ]

    for ezone in unavailable_linked_ezs:
        exclusive = True
        granted, reason = can_lock_exclusion_zone(
            dbsession,
            ezone,
            sherpa,
            exclusive,
        )
        if not granted:
            return granted, reason, []

    reason = "all visas reqd are available"
    return True, reason, reqd_ezones


def get_visas_to_release(dbsession: DBSession, sherpa: fm.Sherpa, req: rqm):
    visa_type = req.visa_type
    zone_name = req.zone_name

    reqd_zone_types = get_reqd_zone_types(visa_type)
    reqd_zone_ids = get_reqd_zone_ids(zone_name, reqd_zone_types)
    visas_to_release = dbsession.get_reqd_ezones(reqd_zone_ids)

    return visas_to_release
