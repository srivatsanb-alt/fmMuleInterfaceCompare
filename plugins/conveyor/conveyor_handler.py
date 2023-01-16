import logging
from .conveyor_utils import book_trip, get_tote_trip_info
from .conveyor_models import ConvInfo, DBSession, ToteStatus


class CONV_HANDLER:
    def init_handler(self):
        self.plugin_name = "plugin_conveyor"

    def handle_tote_status(self, msg: dict):
        tote_status = ToteStatus.from_dict(msg)
        conv_info: ConvInfo = (
            self.session.session.query(ConvInfo)
            .filter(ConvInfo.name == tote_status.name)
            .one_or_none()
        )

        if conv_info is None:
            raise ValueError(f"No conveyor named {tote_status.name} in plugin_conveyor db")

        conv_info.num_totes = tote_status.num_totes

        tote_trip_info = get_tote_trip_info(
            self.session, conv_info.num_totes, tote_status.name, self.plugin_name
        )

        self.logger.info(f"Tote trip info for {tote_status.name} : {tote_trip_info}")

        if tote_trip_info.get("book_trip", False):
            route = []
            nearest_chute = conv_info.nearest_chute
            route = [conv_info.name, nearest_chute]
            book_trip(self.session, route, self.plugin_name)
        else:
            self.logger.info(f"No new trip needs to be booked for {tote_status.name}")

    def handle_tote_trip_info(self, msg):
        conveyor_name = msg["name"]
        conv_info: ConvInfo = (
            self.session.session.query(ConvInfo)
            .filter(ConvInfo.name == conveyor_name)
            .one_or_none()
        )
        if conv_info is None:
            raise ValueError(f"No conveyor named {conveyor_name} in plugin_conveyor db")

        tote_trip_info = get_tote_trip_info(
            self.session, conv_info.num_totes, conveyor_name, self.plugin_name
        )

        return tote_trip_info

    def handle(self, msg):
        msg_type = msg.get("type", "unknown")
        self.init_handler()
        with DBSession() as dbsession:
            self.session = dbsession

            # setup logger
            self.logger = logging.getLogger("plugin_conveyor")
            self.logger.info(f"got a message {msg}")

            # get handler for the msg
            fn_handler = getattr(self, f"handle_{msg_type}", None)
            if not fn_handler:
                self.logger.info(f"Cannot handle msg, {msg}")
                return
            msg["name"] = msg["unique_id"]

            response = fn_handler(msg)

            return response
