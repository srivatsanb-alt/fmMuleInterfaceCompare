import imp
from core.db import session_maker
from models.fleet_models import SherpaModel

# def add_or_update_fleet(name: str, customer=None, site=None, location=None,)


def add_or_update_sherpa(
    sherpa: str, hwid=None, ip_address=None, hashed_api_key=None, fleet_id=None
):
    with session_maker() as db:
        sherpa = SherpaModel(
            name=sherpa,
            hwid=hwid,
            ip_address=ip_address,
            hashed_api_key=hashed_api_key,
            disabled=False,
            pose=None,
            fleet_id=fleet_id,
        )
        db.add(sherpa)
        db.commit()
