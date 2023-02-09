import logging
import hashlib
from .summon_models import SummonInfo, DBSession
from .summon_utils import SummonInfo, DBSession
from .summon_utils import book_trip
import redis
import os

class ButtonPress:
    ENABLE_DISABLE = "enable_disable"
    BOOK_TRIP = "book_trip"
    CANCEL_TRIP = "cancel_trip"


class SUMMON_HANDLER:
    def init_handler(self):
        self.plugin_name = "plugin_summon_button"
    
    def send_msg(self, msg):
        pub = redis.from_url(os.getenv("FM_REDIS_URI"), decode_responses=True)
        pub.publish("channel:plugin_summon_button", str(msg))

    def handle_button_pressed(self, msg: dict):
        hashed_api_key = hashlib.sha256(msg["api_key"].encode("utf-8")).hexdigest()

        self.logger.info("Handling summon button:")
        summon_info: SummonInfo = (
            self.session.session.query(SummonInfo)
            .filter(SummonInfo.hashed_api_key == hashed_api_key)
            .one_or_none()
        )
        if not summon_info:
            raise ValueError("Got msg from an unknown summon button")

        if summon_info.press == ButtonPress.BOOK_TRIP:
            if summon_info.booking_id is None:
                book_trip(
                    self.session,
                    summon_info,
                    route=summon_info.route,
                    plugin_name="plugin_summon_button",
                )
            # else:
            #     cancel_trip(
            #         self.session,
            #         summon_info,
            #         trip_id=summon_info.trip_id,
            #         plugin_name="plugin_summon_button",
            #     )


    def handle(self, msg):
        msg_type = msg.get("type", "unknown")
        self.init_handler()
        with DBSession() as dbsession:
            self.session = dbsession
            self.logger = logging.getLogger("plugin_summon_button")
            self.logger.info(f"got a message {msg}")
            fn_handler = getattr(self, f"handle_{msg_type}", None)
            if not fn_handler:
                self.logger.info(f"Cannot handle msg, {msg}")
                return
            fn_handler(msg)
