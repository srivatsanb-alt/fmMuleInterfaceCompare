import logging
import os
from sqlalchemy import (
    ARRAY,
    Boolean,
    Column,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    DateTime,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine
from sqlalchemy import Integer, String, Column, ARRAY
from sqlalchemy.orm.attributes import flag_modified
from models.base_models import Base, TimestampMixin
import plugins.plugin_comms as pcomms
import models.trip_models as tm
import plugins.ies.ies_utils as iu


class DBSession:
    def __init__(self):
        engine = create_engine(os.path.join(os.getenv("FM_DATABASE_URI"), "plugin_ies"))
        session_maker = sessionmaker(autocommit=False, autoflush=True, bind=engine)
        self.session: Session = session_maker()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type or exc_value or traceback:
            self.close(commit=False)
        else:
            self.close()

    def close(self, commit=True):
        if commit:
            self.session.commit()
        self.session.close()

    def add_to_session(self, obj):
        self.session.add(obj)
        self.session.flush()
        self.session.refresh(obj)

    def get_ati_station_name(self, ies_station_name):
        station = (
            self.session.query(IESStations)
            .filter(IESStations.ies_name == ies_station_name)
            .one_or_none()
        )
        if station is None:
            return None
        return station.ati_name

    def get_consolidation_info(
        self, start_station: str, route_tag: str, booked_from, booked_till
    ):
        all_ies_routes = self.get_all_ies_routes()
        if all_ies_routes != {}:
            logging.getLogger("plugin_ies").info(
                f"filtering bookings, route: {all_ies_routes[route_tag]}"
            )
            filtered_bookings = (
                self.session.query(IESBookingReq)
                .filter(IESBookingReq.start_station == start_station)
                .filter(IESBookingReq.status == "pending")
                .filter(IESBookingReq.route_tag == route_tag)
                .filter(IESBookingReq.combined_trip_id == None)
                .filter(IESBookingReq.created_at > booked_from)
                .filter(IESBookingReq.created_at < booked_till)
                .order_by(IESBookingReq.created_at.desc())
                .all()
            )
        else:
            raise ValueError(f"No IES routes defined")
        return filtered_bookings

    def get_all_ies_routes(self):
        all_ies_routes = self.session.query(IESRoutes).all()
        routes = {}
        for ies_route in all_ies_routes:
            routes.update({ies_route.route_tag: ies_route.route})
        return routes

    def get_all_ies_sherpas(self):
        all_ies_sherpas = self.session.query(IESInfo).first()
        return all_ies_sherpas.ies_sherpas

    def modify_ies_info(self, sherpa_name, enable):
        ies_info = self.session.query(IESInfo).first()
        sherpas = ies_info.ies_sherpas
        # remove from list if disable and entry exists
        if sherpa_name in sherpas and not enable:
            sherpas.remove(sherpa_name)
        else:
            sherpas.append(sherpa_name) if sherpa_name not in sherpas else sherpas

        ies_info.ies_sherpas = sherpas
        flag_modified(ies_info, "ies_sherpas")

        logging.getLogger("plugin_ies").info(f"committing to db {ies_info.ies_sherpas}")
        return

    def modify_ies_routes(self, route_tag, enable):
        ies_route = (
            self.session.query(IESRoutes)
            .filter(IESRoutes.route_tag == route_tag)
            .one_or_none()
        )
        if ies_route is not None and not enable:
            self.session.delete(ies_route)
        # else get saved route from route tag, and then add it to IES db
        else:
            route = iu.get_saved_route(route_tag)
            self.add_to_session(route)
        return

    def get_ongoing_jobs(self, booked_from, booked_till):
        return (
            self.session.query(IESBookingReq)
            .filter(IESBookingReq.combined_trip_id != None)
            .filter(IESBookingReq.status.not_in(tm.COMPLETED_TRIP_STATUS))
            .filter(IESBookingReq.created_at > booked_from)
            .filter(IESBookingReq.created_at < booked_till)
            .order_by(IESBookingReq.created_at.desc())
            .all()
        )

    def get_completed_jobs(self, booked_from, booked_till):
        return (
            self.session.query(IESBookingReq)
            .filter(IESBookingReq.status.in_(tm.COMPLETED_TRIP_STATUS))
            .filter(IESBookingReq.created_at > booked_from)
            .filter(IESBookingReq.created_at < booked_till)
            .order_by(IESBookingReq.created_at.desc())
            .all()
        )

    def get_pending_jobs(self, booked_from, booked_till):
        return (
            self.session.query(IESBookingReq)
            .filter(IESBookingReq.status == "pending")
            .filter(IESBookingReq.created_at > booked_from)
            .filter(IESBookingReq.created_at < booked_till)
            .order_by(IESBookingReq.created_at.desc())
            .all()
        )

    def get_jobs_between_time(self, booked_from, booked_till):
        return (
            self.session.query(IESBookingReq)
            .filter(IESBookingReq.created_at > booked_from)
            .filter(IESBookingReq.created_at < booked_till)
            .all()
        )

    def get_ongoing_combined_trips(self):
        return (
            self.session.query(CombinedTrips)
            .filter(CombinedTrips.status.not_in(tm.COMPLETED_TRIP_STATUS))
            .all()
        )

    def get_active_booking_reqs_for_combined_trip(self, combined_trip):
        return (
            self.session.query(IESBookingReq)
            .filter(IESBookingReq.combined_trip_id == combined_trip.trip_id)
            .filter(IESBookingReq.status.not_in(tm.COMPLETED_TRIP_STATUS))
            .all()
        )

    def get_ext_ref_ids_for_trip(self, combined_trip):
        booking_reqs = combined_trip.trips
        ext_ref_ids = []
        for booking_req in booking_reqs:
            ext_ref_ids.append(booking_req.ext_ref_id)

    def delete_old_bookings_and_combined_trips(self, datetime):
        logging.getLogger("plugin_ies").info(f"deleting old bookings before {datetime}")
        self.session.query(IESBookingReq).filter(
            IESBookingReq.status.in_(tm.COMPLETED_TRIP_STATUS)
        ).filter(IESBookingReq.updated_at < datetime).delete()
        self.session.query(CombinedTrips).filter(
            CombinedTrips.status.in_(tm.COMPLETED_TRIP_STATUS)
        ).filter(CombinedTrips.updated_at < datetime).delete()


class IESBookingReq(Base, TimestampMixin):
    __tablename__ = "ies_booking_req"
    __table_args__ = {"extend_existing": True}
    ext_ref_id = Column(String, primary_key=True, index=True)
    start_station = Column(String, index=True)
    route = Column(ARRAY(String), index=True)
    route_tag = Column(String, index=True)
    status = Column(String, index=True)
    kanban_id = Column(String, index=True)
    deadline = Column(String, index=True)
    combined_trip_id = Column(ForeignKey("combined_trips.trip_id"), index=True)
    combined_trip = relationship(
        "CombinedTrips",
        back_populates="trips",
        uselist=False,
    )
    other_info = Column(JSONB)


class CombinedTrips(Base, TimestampMixin):
    __tablename__ = "combined_trips"
    __table_args__ = {"extend_existing": True}
    trip_id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, index=True)
    combined_route = Column(ARRAY(String))
    sherpa = Column(String, index=True)
    status = Column(String, index=True)
    next_idx_aug = Column(Integer)
    trips = relationship("IESBookingReq", back_populates="combined_trip")


class IESStations(Base):
    __tablename__ = "ies_stations"
    __table_args__ = {"extend_existing": True}
    id = Column(Integer, primary_key=True, index=True)
    ies_name = Column(String, unique=True, index=True)
    ati_name = Column(String, unique=True, index=True)


class IESRoutes(Base):
    __tablename__ = "ies_routes"
    __table_args__ = {"extend_existing": True}
    id = Column(Integer, primary_key=True)
    route_tag = Column(String)
    route = Column(ARRAY(String))


class IESInfo(Base):
    __tablename__ = "ies_info"
    __table_args__ = {"extend_existing": True}
    id = Column(Integer, primary_key=True)
    consolidate = Column(Boolean)
    ies_version = Column(Float)
    ies_sherpas = Column(ARRAY(String), default=[])
    backup_days = Column(Integer, default=30)
    max_bookings = Column(Integer, default=36)
