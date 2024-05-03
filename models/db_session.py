import datetime
import os
from typing import List
from sqlalchemy import func, any_, or_, and_, extract, text
from sqlalchemy.orm import Session
from fastapi.encoders import jsonable_encoder

# ati code imports
from core.db import get_session, get_session_with_engine
import models.misc_models as mm
import models.fleet_models as fm
import models.trip_models as tm
import models.visa_models as vm
from utils.util import check_if_timestamp_has_passed, str_to_dt


class DBSession:
    def __init__(self, engine=None):
        if engine:
            self.session: Session = get_session_with_engine(engine)
        else:
            self.session: Session = get_session(
                os.path.join(os.getenv("FM_DATABASE_URI"), os.getenv("PGDATABASE"))
            )

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

    def close_on_error(self):
        self.session.close()

    def add_to_session(self, obj):
        self.session.add(obj)
        self.session.flush()
        self.session.refresh(obj)

    def create_trip(
        self,
        route,
        priority,
        metadata=None,
        booking_id=None,
        fleet_name=None,
        booked_by=None,
    ):
        trip = tm.Trip(
            route=route,
            priority=priority,
            metadata=metadata,
            fleet_name=fleet_name,
            booking_id=booking_id,
            booked_by=booked_by,
        )
        self.add_to_session(trip)
        return trip

    def get_customer_names(self):
        customer_names = []
        cns = self.session.query(fm.Fleet.customer).distinct().all()
        for cn in cns:
            customer_names.append(cn[0])

        return customer_names

    def create_pending_trip(self, trip_id):
        pending_trip = tm.PendingTrip(trip_id=trip_id)
        self.add_to_session(pending_trip)
        return pending_trip

    def create_ongoing_trip(self, sherpa, trip_id):
        ongoing_trip = tm.OngoingTrip(sherpa_name=sherpa, trip_id=trip_id)
        self.add_to_session(ongoing_trip)
        ongoing_trip.init()
        return ongoing_trip

    def create_trip_leg(self, trip_id, curr_station: str, next_station: str):
        trip_leg = tm.TripLeg(trip_id, curr_station, next_station)
        self.add_to_session(trip_leg)
        return trip_leg

    def get_new_booking_id(self):
        booking_id = self.session.query(func.max(tm.Trip.booking_id)).first()
        if booking_id[0]:
            return booking_id[0] + 1
        return 1

    def get_fleet(self, fleet_name: str) -> fm.Fleet:
        return (
            self.session.query(fm.Fleet).filter(fm.Fleet.name == fleet_name).one_or_none()
        )

    def create_exclusion_zone(self, zone_name, zone_type):
        zone_id = f"{zone_name}_{zone_type}"
        ezone = vm.ExclusionZone(zone_id=zone_id)
        self.add_to_session(ezone)
        return ezone

    def add_linked_zone(self, zone_name, zone_type, linked_zone_name, linked_zone_type):
        ezone = self.get_exclusion_zone(zone_name, zone_type)
        linked_ezone = self.get_exclusion_zone(linked_zone_name, linked_zone_type)
        ezone.prev_linked_gates.append(linked_ezone)
        linked_ezone.next_linked_gates.append(ezone)

    def get_all_locked_ezones(self):
        return (
            self.session.query(vm.ExclusionZone)
            .join(vm.VisaAssignment, vm.ExclusionZone.zone_id == vm.VisaAssignment.zone_id)
            .all()
        )

    def get_reqd_ezones(self, reqd_zone_ids):
        return (
            self.session.query(vm.ExclusionZone)
            .filter(vm.ExclusionZone.zone_id == any_(reqd_zone_ids))
            .all()
        )

    def get_unavailable_reqd_ezones(self, reqd_zone_ids):
        return (
            self.session.query(vm.ExclusionZone)
            .join(vm.VisaAssignment, vm.ExclusionZone.zone_id == vm.VisaAssignment.zone_id)
            .filter(vm.ExclusionZone.zone_id == any_(reqd_zone_ids))
            .all()
        )

    def get_visa_assignment(self, sherpa_name: str):
        return (
            self.session.query(vm.VisaAssignment)
            .filter(vm.VisaAssignment.sherpa_name == sherpa_name)
            .all()
        )

    def get_all_visa_assignments(self):
        return self.session.query(vm.VisaAssignment).all()

    def get_all_visa_rejects(self):
        return self.session.query(vm.VisaRejects).all()

    def get_visa_rejects(self, reqd_ezones, sherpa_name):
        visa_rejects = []
        for ezone in set(reqd_ezones):
            visa_rejects.append(
                self.session.query(vm.VisaRejects)
                .filter(vm.VisaRejects.sherpa_name == sherpa_name)
                .filter(vm.VisaRejects.zone_id == ezone.zone_id)
                .one_or_none()
            )
        return visa_rejects

    def get_all_fleets(self) -> List[fm.Fleet]:
        return self.session.query(fm.Fleet).all()

    def get_all_fleet_names(self) -> List[str]:
        all_fleets = self.session.query(fm.Fleet).all()
        fleet_names = []
        for fleet in all_fleets:
            fleet_names.append(fleet.name)
        return fleet_names

    def get_map_files(self, fleet_name: str) -> List[fm.MapFile]:
        fleet: fm.Fleet = (
            self.session.query(fm.Fleet).filter(fm.Fleet.name == fleet_name).one()
        )
        return (
            self.session.query(fm.MapFile).filter(fm.MapFile.map_id == fleet.map_id).all()
        )

    def get_sherpa(self, name: str) -> fm.Sherpa:
        return self.session.query(fm.Sherpa).filter(fm.Sherpa.name == name).one_or_none()

    def get_sherpa_with_hwid(self, hwid: str) -> fm.Sherpa:
        return self.session.query(fm.Sherpa).filter(fm.Sherpa.hwid == hwid).one_or_none()

    def get_sherpa_with_hashed_api_key(self, hashed_api_key: str) -> fm.Sherpa:
        return (
            self.session.query(fm.Sherpa)
            .filter(fm.Sherpa.hashed_api_key == hashed_api_key)
            .one_or_none()
        )

    def get_all_sherpa_names(self) -> List[str]:
        all_sherpas = self.session.query(fm.Sherpa).all()
        sherpa_names = []
        for sherpa in all_sherpas:
            sherpa_names.append(sherpa.name)
        return sherpa_names

    def get_all_sherpas(self) -> List[fm.Sherpa]:
        return self.session.query(fm.Sherpa).all()

    def get_all_sherpas_in_fleet(self, fleet_name: str) -> List[fm.Sherpa]:
        return (
            self.session.query(fm.Sherpa)
            .join(fm.Sherpa.fleet)
            .filter(fm.Fleet.name == fleet_name)
            .all()
        )

    def get_sherpa_availability(self, sherpa_name: str):
        return (
            self.session.query(fm.AvailableSherpas)
            .filter(fm.AvailableSherpas.sherpa_name == sherpa_name)
            .one_or_none()
        )

    def get_all_available_sherpa_names(self, fleet_name: str):
        available_sherpa_names = []

        temp = (
            self.session.query(fm.AvailableSherpas.sherpa_name)
            .filter(fm.AvailableSherpas.fleet_name == fleet_name)
            .filter(fm.AvailableSherpas.available.is_(True))
            .all()
        )
        for val in temp:
            available_sherpa_names.append(val[0])

        return available_sherpa_names

    def get_all_sherpa_status(self) -> List[fm.SherpaStatus]:
        return self.session.query(fm.SherpaStatus).all()

    def get_all_stale_sherpa_status(self, heartbeat_interval):
        filter_time = datetime.datetime.now() + datetime.timedelta(
            seconds=-heartbeat_interval
        )
        return (
            self.session.query(fm.SherpaStatus)
            .filter(
                or_(
                    fm.SherpaStatus.updated_at < filter_time,
                    fm.SherpaStatus.updated_at == None,
                )
            )
            .all()
        )

    def get_sherpa_status(self, name: str) -> fm.SherpaStatus:
        return (
            self.session.query(fm.SherpaStatus)
            .filter(fm.SherpaStatus.sherpa_name == name)
            .one()
        )

    def get_sherpa_events(self, sherpa_name: str, num_events=10) -> List[fm.SherpaEvent]:
        return (
            self.session.query(fm.SherpaEvent)
            .filter(fm.SherpaEvent.sherpa_name == sherpa_name)
            .order_by(fm.SherpaEvent.created_at.desc())
            .limit(num_events)
            .all()
        )

    def get_sherpa_metadata(self, sherpa_name: str):
        return (
            self.session.query(fm.SherpaMetaData)
            .filter(fm.SherpaMetaData.sherpa_name == sherpa_name)
            .one_or_none()
        )

    def delete_stale_sherpa_events(self, sherpa_name: str):
        stale_sherpa_events = self.session.query(fm.SherpaEvent).filter(
            fm.SherpaEvent.sherpa_name == sherpa_name
        )[:-10]
        for stale_sherpa_event in stale_sherpa_events:
            self.session.delete(stale_sherpa_event)

    def get_station_if_present(self, name: str) -> fm.Station:
        return self.session.query(fm.Station).filter(fm.Station.name == name).one_or_none()

    def get_station(self, name: str) -> fm.Station:
        return self.session.query(fm.Station).filter(fm.Station.name == name).one()

    def get_station_with_pose(self, pose: list) -> fm.Station:
        return self.session.query(fm.Station).filter(fm.Station.pose == pose).one_or_none()

    def get_all_stations(self) -> List[fm.Station]:
        return self.session.query(fm.Station).all()

    def get_all_stations_in_fleet(self, fleet_name: str) -> List[fm.Station]:
        return (
            self.session.query(fm.Station)
            .join(fm.Station.fleet)
            .filter(fm.Fleet.name == fleet_name)
            .all()
        )

    def get_station_status(self, name: str) -> fm.StationStatus:
        return (
            self.session.query(fm.StationStatus)
            .filter(fm.StationStatus.station_name == name)
            .one()
        )

    def get_all_station_status(self) -> List[fm.StationStatus]:
        return self.session.query(fm.StationStatus).all()

    def get_fleet_name_from_route(self, route: List):
        prev_fleet_name = None
        fleet_name = None
        for station_name in route:
            station = (
                self.session.query(fm.Station).filter(fm.Station.name == station_name).one()
            )
            fleet_name = station.fleet.name
            if prev_fleet_name and prev_fleet_name != fleet_name:
                raise Exception(
                    "invalid route, all stations should belong to the same fleet"
                )
            prev_fleet_name = fleet_name

        return fleet_name

    def get_trip(self, trip_id):
        return self.session.query(tm.Trip).filter(tm.Trip.id == trip_id).one()

    def get_trips_with_booking_id(self, booking_id):
        return self.session.query(tm.Trip).filter(tm.Trip.booking_id == booking_id).all()

    def get_pending_trip(self, sherpa_name: str):
        pending_trips = (
            self.session.query(tm.PendingTrip)
            .filter(tm.PendingTrip.sherpa_name == sherpa_name)
            .all()
        )

        for pending_trip in pending_trips:
            if pending_trip.trip.scheduled:
                trip_metadata = pending_trip.trip.trip_metadata
                scheduled_start_time = str_to_dt(trip_metadata["scheduled_start_time"])
                if not check_if_timestamp_has_passed(scheduled_start_time):
                    continue
            return pending_trip
        return None

    def get_pending_trips_with_fleet_name(self, fleet_name: str):
        return (
            self.session.query(tm.PendingTrip)
            .join(tm.PendingTrip.trip)
            .filter(tm.Trip.fleet_name == fleet_name)
            .all()
        )

    def get_sherpas_with_pending_trip(self):
        sherpas = []
        temp = self.session.query(tm.PendingTrip.sherpa_name).all()
        for val in temp:
            sherpas.append(val[0])
        return sherpas

    def get_ongoing_trip(self, sherpa_name: str):
        return (
            self.session.query(tm.OngoingTrip)
            .filter(tm.OngoingTrip.sherpa_name == sherpa_name)
            .one_or_none()
        )

    def get_enroute_trip(self, sherpa_name: str):
        return (
            self.session.query(tm.Trip)
            .filter(tm.Trip.sherpa_name == sherpa_name)
            .filter(tm.Trip.status == "en_route")
            .one_or_none()
        )

    def get_all_ongoing_trips(self):
        return self.session.query(tm.OngoingTrip).all()

    def get_all_ongoing_trips_fleet(self, fleet_name: str):
        return (
            self.session.query(tm.OngoingTrip)
            .join(tm.OngoingTrip.trip)
            .filter(tm.Trip.fleet_name == fleet_name)
            .all()
        )

    def get_ongoing_trip_with_trip_id(self, trip_id):
        return (
            self.session.query(tm.OngoingTrip)
            .filter(tm.OngoingTrip.trip_id == trip_id)
            .one_or_none()
        )

    def get_pending_trip_with_trip_id(self, trip_id):
        return (
            self.session.query(tm.PendingTrip)
            .filter(tm.PendingTrip.trip_id == trip_id)
            .one_or_none()
        )

    def get_trip_with_booking_id(self, booking_id):
        return self.session.query(tm.Trip).filter(tm.Trip.booking_id == booking_id).all()

    def get_last_trip(self, sherpa_name):
        return (
            self.session.query(tm.Trip)
            .filter(tm.Trip.sherpa_name == sherpa_name)
            .filter(tm.Trip.end_time != None)
            .order_by(tm.Trip.end_time.desc())
            .first()
        )

    def get_saved_route(self, tag: str) -> tm.SavedRoutes:
        return (
            self.session.query(tm.SavedRoutes)
            .filter(tm.SavedRoutes.tag == tag)
            .one_or_none()
        )

    def get_saved_routes_fleet(self, fleet_name) -> List[tm.SavedRoutes]:
        return (
            self.session.query(tm.SavedRoutes)
            .filter(tm.SavedRoutes.fleet_name == fleet_name)
            .all()
        )

    def get_trips_with_timestamp_and_status_pagination(
        self,
        from_dt,
        to_dt,
        filter_fleets,
        valid_status,
        sherpa_names,
        filter_status,
        search_text,
        sort_field="id",
        sort_order="desc",
        page=0,
        limit=50,
    ):
        skip = page * limit
        trips = {}
        count = 0
        base_query = self.session.query(tm.Trip).filter(tm.Trip.status.in_(valid_status))
        if from_dt and from_dt != "":
            base_query = base_query.filter(
                or_(tm.Trip.booking_time >= from_dt, tm.Trip.start_time >= from_dt)
            )
        if to_dt and to_dt != "":
            base_query = base_query.filter(
                or_(tm.Trip.booking_time <= to_dt, tm.Trip.end_time <= to_dt)
            )
        if filter_fleets and filter_fleets != "[]":
            base_query = base_query.filter(tm.Trip.fleet_name.in_(filter_fleets))
        if sherpa_names and sherpa_names != "[]":
            base_query = base_query.filter(tm.Trip.sherpa_name.in_(sherpa_names))

        # having to filter again due to filter in UI that overrides above filter
        if filter_status and filter_status != "[]":
            base_query = base_query.filter(tm.Trip.status.in_(filter_status))

        if search_text and search_text != "":
            columns_to_search = [
                tm.Trip.sherpa_name,
                tm.Trip.status,
                tm.Trip.booked_by,
            ]
            conditions = or_(
                *[column.ilike(f"%{search_text}%") for column in columns_to_search]
            )
            base_query = base_query.filter(conditions)

        count = base_query.count()

        base_query = (
            base_query.order_by(text(f"{sort_field} {sort_order}"))
            .offset(skip)
            .limit(limit)
        )

        trips = base_query.all()

        pages = int(count / limit) if (count % limit == 0) else int(count / limit + 1)

        trips = jsonable_encoder(trips)

        for item in trips:
            item["progress"] = self.get_trip_progress(str(item["id"]))
        trips = {
            "trips": trips,
            "count": count,
            "limit": limit,
            "total_pages": pages,
            "sort_field": sort_field,
            "sort_order": sort_order,
        }
        return trips

    def get_trips_with_timestamp_and_status(self, from_dt, to_dt, valid_status):
        return (
            self.session.query(tm.Trip)
            .filter(or_(tm.Trip.booking_time >= from_dt, tm.Trip.start_time >= from_dt))
            .filter(or_(tm.Trip.booking_time <= to_dt, tm.Trip.end_time <= to_dt))
            .filter(tm.Trip.status.in_(valid_status))
            .order_by(tm.Trip.id.desc())
            .all()
        )

    def get_trips_with_ids_and_status(self, trip_ids, valid_status):
        return (
            self.session.query(tm.Trip)
            .filter(tm.Trip.id.in_(trip_ids))
            .filter(tm.Trip.status.in_(valid_status))
            .order_by(tm.Trip.id.desc())
            .all()
        )

    def get_trips_with_timestamp(self, from_dt, to_dt):
        return (
            self.session.query(tm.Trip)
            .filter(or_(tm.Trip.booking_time >= from_dt, tm.Trip.start_time >= from_dt))
            .filter(or_(tm.Trip.booking_time <= to_dt, tm.Trip.end_time <= to_dt))
            .order_by(tm.Trip.id.desc())
            .all()
        )

    def get_trips_with_ids(self, trip_ids):
        return (
            self.session.query(tm.Trip)
            .filter(tm.Trip.id.in_(trip_ids))
            .order_by(tm.Trip.id.desc())
            .all()
        )

    def get_trip_analytics_with_timestamp(self, from_dt, to_dt):
        return (
            self.session.query(tm.TripAnalytics)
            .join(tm.Trip, (tm.TripAnalytics.trip_id == tm.Trip.id))
            .filter(or_(tm.Trip.booking_time >= from_dt, tm.Trip.start_time >= from_dt))
            .filter(or_(tm.Trip.booking_time <= to_dt, tm.Trip.end_time <= to_dt))
            .order_by(tm.TripAnalytics.trip_leg_id.desc())
            .all()
        )

    def get_trip_analytics_with_trip_ids(self, trip_ids):
        return (
            self.session.query(tm.TripAnalytics)
            .join(tm.Trip, (tm.TripAnalytics.trip_id == tm.Trip.id))
            .filter(tm.Trip.id.in_(trip_ids))
            .order_by(tm.TripAnalytics.trip_leg_id.desc())
            .all()
        )

    def get_trip_progress(self, trip_id):
        progress = (
            self.session.query(tm.TripAnalytics.progress)
            .filter(tm.TripAnalytics.trip_id == trip_id)
            .first()
        )
        return jsonable_encoder(progress)

    def get_legs(self, trip_id):
        legs = (
            self.session.query(tm.TripAnalytics)
            .filter(tm.TripAnalytics.trip_id == trip_id)
            .all()
        )
        return jsonable_encoder(legs)

    def get_trip_analytics_with_pagination(
        self,
        from_dt,
        to_dt,
        filter_fleets,
        sherpa_names,
        sort_field="id",
        sort_order="desc",
        page=0,
        limit=50,
    ):
        # data validation
        if limit == 0:
            limit = 50
        if sort_field == "":
            sort_field = "id"
        if sort_order == "":
            sort_order = "desc"
        # Data validation
        skip = page * limit
        trip_analytics = {}
        count = 0

        base_query = (
            self.session.query(tm.Trip)
            .filter(tm.Trip.start_time >= from_dt)
            .filter(tm.Trip.end_time <= to_dt)
        )

        if filter_fleets and filter_fleets != "[]":
            base_query = base_query.filter(tm.Trip.fleet_name.in_(filter_fleets))

        if sherpa_names and sherpa_names != "[]":
            base_query = base_query.filter(tm.Trip.sherpa_name.in_(sherpa_names))

        count = base_query.count()

        base_query = (
            base_query.order_by(text(f"{sort_field} {sort_order}"))
            .offset(skip)
            .limit(limit)
        )

        trips = base_query.all()

        pages = int(count / limit) if (count % limit == 0) else int(count / limit + 1)

        trip_analytics = jsonable_encoder(trips)
        for item in trip_analytics:
            item["legs"] = self.get_legs(str(item["id"]))
        trip_analytics = {
            "trips_analytics": trip_analytics,
            "count": count,
            "limit": limit,
            "total_pages": pages,
            "sort_field": sort_field,
            "sort_order": sort_order,
        }
        return trip_analytics

    def get_trip_analytics(self, trip_leg_id):
        return (
            self.session.query(tm.TripAnalytics)
            .filter(tm.TripAnalytics.trip_leg_id == trip_leg_id)
            .one_or_none()
        )

    def get_last_n_trips(self, last_n=10):
        return self.session.query(tm.Trip).order_by(tm.Trip.id.desc()).limit(last_n).all()

    def get_trip_leg(self, sherpa_name: str):
        ongoing_trip: tm.OngoingTrip = self.get_ongoing_trip(sherpa_name)
        if ongoing_trip:
            return (
                self.session.query(tm.TripLeg)
                .filter(tm.TripLeg.id == ongoing_trip.trip_leg_id)
                .one_or_none()
            )

    def get_all_trip_legs(self, trip_id: int):
        temp = self.session.query(tm.TripLeg.id).filter(tm.TripLeg.trip_id == trip_id).all()
        trip_leg_ids = []
        for vals in temp:
            trip_leg_ids.append(vals[0])
        return trip_leg_ids

    def get_exclusion_zone(self, zone_name, zone_type) -> vm.ExclusionZone:
        zone_id = f"{zone_name}_{zone_type}"
        return (
            self.session.query(vm.ExclusionZone)
            .filter(vm.ExclusionZone.zone_id == zone_id)
            .one_or_none()
        )

    def delete_pending_trip(self, pending_trip):
        self.session.delete(pending_trip)

    def delete_ongoing_trip(self, ongoing_trip):
        self.session.delete(ongoing_trip)

    def add_notification(
        self, entity_names, log, log_level, module, repetitive=False, repetition_freq=None
    ):
        new_notification = mm.Notifications(
            entity_names=entity_names,
            log=log,
            log_level=log_level,
            module=module,
            cleared_by=[],
            repetitive=repetitive,
            repetition_freq=repetition_freq,
        )
        self.add_to_session(new_notification)

    def get_notifications(self):
        return self.session.query(mm.Notifications).all()

    def get_notifications_filter_with_log_level(self, log_level):
        return (
            self.session.query(mm.Notifications)
            .filter(mm.Notifications.log_level == log_level)
            .all()
        )

    def get_notification_count(self):
        return self.session.query(mm.Notifications).count()

    def any_new_addition_to_notification_table(self, curr_dt):
        new_notifs = (
            self.session.query(mm.Notifications)
            .filter(
                or_(
                    mm.Notifications.created_at > curr_dt,
                    mm.Notifications.updated_at > curr_dt,
                )
            )
            .all()
        )
        if len(new_notifs) == 0:
            return False

        return True

    def yield_notifications_grouped_by_log_level_and_modules(
        self, fleet_name, skip_log_levels=[], skip_modules=[]
    ):

        all_distinct_modules = self.session.query(
            func.distinct(mm.Notifications.module)
        ).all()
        all_log_levels = self.session.query(func.distinct(mm.Notifications.log_level)).all()
        for log_level in all_log_levels:
            if log_level in skip_log_levels:
                continue
            for mod in all_distinct_modules:
                if mod in skip_modules:
                    continue
                temp = (
                    self.session.query(mm.Notifications)
                    .filter(any_(mm.Notifications.entity_names) == fleet_name)
                    .filter(mm.Notifications.log_level == log_level[0])
                    .filter(mm.Notifications.module == mod[0])
                    .all()
                )

                if len(temp) == 0:
                    continue

                yield log_level[0], mod[0], temp

    def delete_all_notifications(self):
        return self.session.query(mm.Notifications).delete()

    def make_pop_ups_stale(self, max_num_pop_up_notifications):
        pop_ups = [mm.NotificationLevels.alert, mm.NotificationLevels.action_request]
        all_stale_pop_ups = self.session.query(mm.Notifications).filter(
            mm.Notifications.log_level.in_(pop_ups)
        )[:-max_num_pop_up_notifications]
        for stale_pop_ups in all_stale_pop_ups:
            stale_pop_ups.log_level = mm.NotificationLevels.stale_alert_or_action

    def delete_old_notifications(self, datetime):
        self.session.query(mm.Notifications).filter(
            mm.Notifications.created_at < datetime
        ).delete()

    def get_notifications_with_id(self, id):
        return (
            self.session.query(mm.Notifications)
            .filter(mm.Notifications.id == id)
            .one_or_none()
        )

    def delete_notification(self, id):
        self.session.query(mm.Notifications).filter(mm.Notifications.id == id).delete()

    def get_compatability_info(self):
        return self.session.query(mm.SoftwareCompatability).one_or_none()

    def get_master_data_upload_info(self):
        return self.session.query(mm.MasterFMDataUploadts).one_or_none()

    def get_fm_incidents(
        self, from_datetime, to_datetime=datetime.datetime.now(), entity_name=None
    ):
        if entity_name:
            return self.session.query(mm.FMIncidents).filter(
                and_(
                    mm.FMIncidents.created_at > from_datetime,
                    mm.FMIncidents.created_at < to_datetime,
                )
                .filter(mm.FMIncidents.entity_name == entity_name)
                .all()
            )
        else:
            return self.session.query(mm.FMIncidents).filter(
                and_(
                    mm.FMIncidents.created_at > from_datetime,
                    mm.FMIncidents.created_at < to_datetime,
                ).all()
            )

    def get_fm_incident(self, incident_id: str):
        return (
            self.session.query(mm.FMIncidents)
            .filter(mm.FMIncidents.incident_id == incident_id)
            .one_or_none()
        )

    def get_recent_fm_incident(self, entity_name, n=1):
        return (
            self.session.query(mm.FMIncidents)
            .filter(mm.FMIncidents.entity_name == entity_name)
            .order_by(mm.FMIncidents.created_at.desc())
            .limit(n)
            .all()
        )
    
    def get_fm_incident_pg(
        self,
        from_dt,
        to_dt,
        error_type="fm_error",
        sort_field="created_at",
        sort_order="desc",
        page=0,
        limit=50,
            
        ):
        skip = page * limit
        
        query = self.session.query(mm.FMIncidents)
        query = query.filter(mm.FMIncidents.type == error_type)
        query = query.filter(mm.FMIncidents.created_at > from_dt)
        query = query.filter(mm.FMIncidents.created_at < to_dt)
        query = query.filter(mm.FMIncidents.updated_at > from_dt)
        query = query.filter(mm.FMIncidents.updated_at < to_dt)

        count = query.count()

        query = (
            query.order_by(text(f"{sort_field} {sort_order}"))
            .offset(skip)
            .limit(limit)
            )
        
        fm_incidents = query.all()

        pages = int(count / limit) if (count % limit == 0) else int(count / limit + 1)
        return fm_incidents, count, limit, pages, sort_field, sort_order
            

    def get_last_sherpa_mode_change(self, sherpa_name):
        return (
            self.session.query(mm.SherpaModeChange)
            .filter(mm.SherpaModeChange.sherpa_name == sherpa_name)
            .order_by(mm.SherpaModeChange.started_at.desc())
            .first()
        )

    def get_sherpa_oee(self, sherpa_name, today_start):
        return (
            self.session.query(mm.SherpaOEE)
            .filter(mm.SherpaOEE.sherpa_name == sherpa_name)
            .filter(mm.SherpaOEE.dt == today_start)
            .one_or_none()
        )

    def get_sherpa_mode_split_up(self, sherpa_name, today_start):
        return (
            self.session.query(
                mm.SherpaModeChange.mode,
                func.sum(
                    extract(
                        "seconds",
                        func.age(
                            mm.SherpaModeChange.ended_at, mm.SherpaModeChange.started_at
                        ),
                    )
                ),
            )
            .filter(mm.SherpaModeChange.sherpa_name == sherpa_name)
            .filter(mm.SherpaModeChange.ended_at > today_start)
            .filter(mm.SherpaModeChange.started_at > today_start)
            .group_by(mm.SherpaModeChange.mode)
            .all()
        )

    def get_sherpa_trip_time_with_timestamp(self, sherpa_name, start_time, end_time):
        trip_time = (
            self.session.query(
                func.sum(
                    extract(
                        "seconds",
                        func.age(tm.Trip.end_time, tm.Trip.start_time),
                    )
                ),
            )
            .filter(tm.Trip.sherpa_name == sherpa_name)
            .filter(tm.Trip.start_time > start_time)
            .filter(tm.Trip.end_time < end_time)
            .all()
        )

        for item in trip_time:
            try:
                return float(item[0])
            except:
                pass

        return None

    def get_popular_routes(self, fleet_name: str):
        return (
            self.session.query(tm.Trip.route)
            .filter(tm.Trip.fleet_name == fleet_name)
            .group_by(tm.Trip.route)
            .order_by(func.count(tm.Trip.route).desc())
            .all()
        )

    def get_file_upload(self, filename: str):
        return (
            self.session.query(mm.FileUploads)
            .filter(mm.FileUploads.filename == filename)
            .one_or_none()
        )

    def get_expected_trip_time(self, from_station, to_station, limit=5):
        subquery = (
            self.session.query(tm.TripAnalytics.actual_trip_time)
            .filter(tm.TripAnalytics.from_station == from_station)
            .filter(tm.TripAnalytics.to_station == to_station)
            .filter(tm.TripAnalytics.actual_trip_time != None)
            .order_by(tm.TripAnalytics.trip_leg_id.desc())
            .limit(10)
            .subquery()
        )
        return self.session.query(func.avg(subquery.c.actual_trip_time)).scalar()

    def get_all_visa_assignments_as_dict(self, zone_id):
        response = []
        sherpas = (
            self.session.query(
                vm.VisaAssignment.sherpa_name,
                vm.VisaAssignment.created_at.label("granted_time"),
            )
            .filter(vm.VisaAssignment.zone_id == zone_id)
            .all()
        )
        waiting_sherpas = (
            self.session.query(
                vm.VisaRejects.sherpa_name,
                vm.VisaRejects.created_at.label("denied_time"),
                vm.VisaRejects.reason,
            )
            .filter(vm.VisaRejects.zone_id == zone_id)
            .all()
        )
        resident_sherpas = jsonable_encoder(sherpas)

        waiting_sherpas = jsonable_encoder(waiting_sherpas)

        response = {
            "resident_sherpas": resident_sherpas,
            "waiting_sherpas": waiting_sherpas,
        }
        return response
