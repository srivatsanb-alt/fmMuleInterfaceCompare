import os

# ati code imports
from core.db import get_session, get_engine
from models.misc_models import FMVersion


AVAILABLE_UPGRADES = [
    "2.2",
    "3.0",
    "3.01",
    "3.1",
    "3.2",
    "3.3",
    "4.0",
    "4.01",
    "4.02",
    "4.1",
    "4.15"
]
NO_SCHEMA_CHANGES = ["3.0", "3.01", "3.1", "4.15"]


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

    def upgrade_to_4_0(self):
        with get_engine(os.getenv("FM_DATABASE_URI")).connect() as conn:
            conn.execute("commit")
            result = conn.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='trip_analytics'"
            )
            column_names = [row[0] for row in result]
            if "route_length" not in column_names:
                conn.execute('ALTER TABLE "trip_analytics" ADD COLUMN "route_length" FLOAT')
                print("column route_length added trip_analytics table")
            else:
                print("column route_length already present in trip_analytics table")

            if "progress" not in column_names:
                conn.execute('ALTER TABLE "trip_analytics" ADD COLUMN "progress" FLOAT')
                print("column progress added trip_analytics table")
            else:
                print("column progress already present in trip_analytics table")

            result = conn.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='trips'"
            )
            column_names = [row[0] for row in result]
            if "route_lengths" not in column_names:
                conn.execute('ALTER TABLE "trips" ADD COLUMN "route_lengths" FLOAT[]')
                print("column route_lengths added trips table")
            else:
                print("column route_lengths already present in trips table")

    def upgrade_to_4_01(self):
        with get_engine(os.getenv("FM_DATABASE_URI")).connect() as conn:
            conn.execute("commit")
            result = conn.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='sherpas'"
            )
            column_names = [row[0] for row in result]
            if "parking_id" not in column_names:
                conn.execute('ALTER TABLE "sherpas" ADD COLUMN "parking_id" VARCHAR')
                conn.execute(
                    'ALTER TABLE "sherpas" ADD CONSTRAINT fk_parking_id FOREIGN KEY (parking_id) REFERENCES stations (name)'
                )
                print("column parking_id added to sherpas table")
            else:
                print("column parking_id already present in sherpa table")

    def upgrade_to_4_02(self):
        ## have no limits on num connections ##
        with get_engine(os.getenv("FM_DATABASE_URI")).connect() as conn:
            conn.execute("commit")
            conn.execute("alter role postgres with connection limit -1")
            print("Set no-limit to num connections")

    def upgrade_to_4_1(self):
        with get_engine(os.getenv("FM_DATABASE_URI")).connect() as conn:
            try:
                conn.execute("commit")
                conn.execute("drop table master_fm_data_upload")
            except Exception as e:
                print(f"Unable to drop master_fm_data_upload, exception: {e}")


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


def maybe_delete_fm_incidents_v3_3():
    # many schema changes ,false positives in fm_incidents data - dropping the table with old data
    with get_engine(os.getenv("FM_DATABASE_URI")).connect() as conn:
        conn.execute("commit")
        result = conn.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='fm_incidents'"
        )
        column_names = [row[0] for row in result]

        # data_path was added post FM_v3.2.1
        if "data_path" not in column_names:
            conn.execute('DROP TABLE "fm_incidents"')
            print("dropped table fm_incidents")

def maybe_delete_visa_related_tables_v4_15():
    with get_engine(os.getenv("FM_DATABASE_URI")).connect() as conn:
        try:
            conn.execute("commit")
            conn.execute("drop table visa_assignments")
            conn.execute("drop table visa_rejects")
            print("dropped visa_assignments and visa_rejects")
        except Exception as e:
            print(f"Unable to drop visa_assignments and visa_rejects, exception: {e}")



def maybe_drop_tables():
    with get_session(os.getenv("FM_DATABASE_URI")) as session:
        try:
            fm_version = session.query(FMVersion).one_or_none()
            if fm_version:
                if float(fm_version.version) <= 3.3:
                    maybe_delete_fm_incidents_v3_3()
                if float(fm_version.version) < 4.15:
                    maybe_delete_visa_related_tables_v4_15()

        except Exception as e:
            print(
                f"Unable tom fetch fm version from DB, cannot drop tables based on fm_version, exception: {e}"
            )
        