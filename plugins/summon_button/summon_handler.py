import logging
import hashlib
from .summon_models import SummonInfo, DBSession
from .summon_utils import book_trip, cancel_trip, send_msg_to_summon_button


class ButtonPress:
    ENABLE_DISABLE = "enable_disable"
    BOOK_TRIP = "book_trip"


class SUMMON_HANDLER:
    def init_handler(self):
        self.plugin_name = "plugin_summon_button"

    def send_msg_to_summon_button(self, msg, unique_id):
        send_msg_to_summon_button(msg, unique_id)

    def handle_button_pressed(self, msg: dict):
        hashed_api_key = msg["api_key"]
        summon_info: SummonInfo = (
            self.session.session.query(SummonInfo)
            .filter(SummonInfo.hashed_api_key == hashed_api_key)
            .one_or_none()
        )
        if not summon_info:
            raise ValueError("Got msg from an unknown summon button")

        if summon_info.press == ButtonPress.BOOK_TRIP:
            if summon_info.booking_id is None:
                self.logger.info("button pressed - booking trip")
                book_trip(
                    self.session,
                    summon_info,
                    route=summon_info.route,
                    plugin_name="plugin_summon_button",
                )
                self.send_msg_to_summon_button({"Led": "green"}, summon_info.id)
            else:
                self.logger.info(
                    f"button pressed - cancelling trip {summon_info.booking_id}"
                )
                cancel_trip(
                    self.session,
                    summon_info,
                    plugin_name="plugin_summon_button",
                )
                self.send_msg_to_summon_button({"Led": "white"}, summon_info.id)

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
