import os

# ati code imports
from core.db import get_session, get_engine
from models.misc_models import FMVersion


AVAILABLE_UPGRADES = ["2.2", "3.0", "3.01", "3.1", "3.2", "3.3"]
NO_SCHEMA_CHANGES = ["3.0", "3.01", "3.1"]


class DBUpgrade:
    def ack_no_schema_change_reqd(self, fm_version):
        print(f"will upgrade db to version {fm_version}")
        print(f"No db schema upgrades required for {fm_version}")

    def upgrade_to_2_2(self):
        with get_engine(os.getenv("FM_DATABASE_URI")).connect() as conn:
            conn.execute("commit")
            conn.execute('CREATE INDEX "booking_time_index" on "trips" ("booking_time")')

    def upgrade_to_3_2(self):
        with get_engine(os.getenv("FM_DATABASE_URI")).connect() as conn:
            conn.execute("commit")
            result = conn.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='trips'"
            )
            column_names = [row[0] for row in result]
            if "booked_by" not in column_names:
                conn.execute('ALTER TABLE "trips" ADD COLUMN "booked_by" VARCHAR')
                print("boooked_by column added trips table")
            else:
                print("booked_by column already present need not be added again")

    def upgrade_to_3_3(self):
        with get_engine(os.getenv("FM_DATABASE_URI")).connect() as conn:
            conn.execute("commit")
            result = conn.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='trip_legs'"
            )
            column_names = [row[0] for row in result]
            if "status" not in column_names:
                conn.execute('ALTER TABLE "trip_legs" ADD COLUMN "status" VARCHAR')
                print("status column added trip_legs table")
            else:
                print("status column already present need not be added again")
            if "stoppage_reason" not in column_names:
                conn.execute('ALTER TABLE "trip_legs" ADD COLUMN "stoppage_reason" VARCHAR')
                print("stoppage_reason column added trip_legs table")
            else:
                print("stoppage_reason column already present need not be added again")


def upgrade_db_schema():

    # fm version records available only after v2.1
    with get_session(os.getenv("FM_DATABASE_URI")) as session:
        fm_version = session.query(FMVersion).one_or_none()
        if not fm_version:
            fm_version = FMVersion(version="2.1")
            session.add(fm_version)
            session.flush()
            session.commit()

        dbupgrade = DBUpgrade()

    # upgrade sequentially

    sorted_upgrades = sorted(AVAILABLE_UPGRADES, key=float)
    for version in sorted_upgrades:
        with get_session(os.getenv("FM_DATABASE_URI")) as session:
            fm_version = session.query(FMVersion).one_or_none()
            if float(fm_version.version) < float(version):
                print(f"Will try to upgrade db from v_{fm_version.version} to v_{version}")
                version_txt = version.replace(".", "_")

                if version in NO_SCHEMA_CHANGES:
                    dbupgrade.ack_no_schema_change_reqd(version)
                else:
                    upgrade_fn = getattr(dbupgrade, f"upgrade_to_{version_txt}", None)
                    if not upgrade_fn:
                        print(
                            f"Invalid upgrade call, cannot upgrade from {fm_version.version} to {version}"
                        )
                        continue
                    upgrade_fn()

                print(f"Successfully upgraded db from {fm_version.version} to {version}")
                fm_version.version = version
                session.commit()
