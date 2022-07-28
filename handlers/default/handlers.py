import logging
from models.db_session import DBSession


session = DBSession()


class Handlers:
    def should_handle_msg(self, msg):
        return True, None

    def handle_init(msg):
        print("all is well with init")
        pass

    def handle(self, msg):
        handle_ok, reason = self.should_handle_msg(msg)
        if not handle_ok:
            logging.getLogger().warning(f"message of type {type} ignored, reason={reason}")
        msg_handler = getattr(self, "handle_" + msg.type)
        msg_handler()
