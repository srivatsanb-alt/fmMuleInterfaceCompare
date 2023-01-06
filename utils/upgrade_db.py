from core.db import session_maker, engine
from models.misc_models import FMVersion


AVAILABLE_UPGRADES = ["2.2"]


class DBUpgrade:
    def upgrade_to_2_2(self):
        print("will upgrade db to version 2.2")
        with engine.connect() as conn:
            conn.execute("commit")
            conn.execute('CREATE INDEX "booking_time_index" on "trips" ("booking_time")')


def upgrade_db_schema():

    # fm version records available only after v2.1
    with session_maker() as dbsession:
        fm_version = dbsession.query(FMVersion).one_or_none()
        if not fm_version:
            fm_version = FMVersion(version="2.1")
            dbsession.add(fm_version)
            dbsession.flush()
            dbsession.commit()

        dbupgrade = DBUpgrade()

    # upgrade sequentially
    for version in AVAILABLE_UPGRADES:
        with session_maker() as dbsession:
            fm_version = dbsession.query(FMVersion).one_or_none()
            if float(fm_version.version) < float(version):
                print(f"Will try to upgrade db from v_{fm_version.version} to v_{version}")
                version_txt = version.replace(".", "_")
                upgrade_fn = getattr(dbupgrade, f"upgrade_to_{version_txt}", None)
                if not upgrade_fn:
                    print(
                        f"Invalid upgrade call, cannot upgrade from {fm_version.version} to {version}"
                    )
                    continue
                upgrade_fn()
                fm_version.version = version
                dbsession.commit()
                print(f"Successfully upgraded db from {fm_version.version} to {version}")
