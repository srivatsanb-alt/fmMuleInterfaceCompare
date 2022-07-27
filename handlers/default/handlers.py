from models.db_session import DBSession
from models.trip_models import Trip


session = DBSession()


class Handlers:
    def should_handle_msg(self, msg):
        return True, None

    def handle(self, msg):
        handle_ok, reason = self.should_handle_msg(msg)
        print("All is well")

    def handle_trip_booking(self, msg):
        route = msg["route"]
        trip = Trip(msg["route"])
