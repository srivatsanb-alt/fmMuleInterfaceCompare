import logging
import logging.config

# ati code imports
from models.db_session import DBSession
import utils.util as utils_util
import core.common as ccm


class RequestContext:
    msg_type: str
    source: str

req_ctxt = RequestContext()

def init_request_context(req):
    req_ctxt.msg_type = req.type
    req_ctxt.source = req.source


class AnalyticsHandler:
    def handle_get_analytics_data(self, req):
        # query db
        from_dt = utils_util.str_to_dt(req.from_dt)
        to_dt = utils_util.str_to_dt(req.to_dt)
        analytics_data = self.dbsession.get_analytics_data(
            req.fleet_name,
            from_dt,
            to_dt
        )
        return analytics_data
    
    
    def handle(self, msg):
        self.dbsession = None
        init_request_context(msg)

        with DBSession(engine=ccm.engine) as dbsession:
            self.dbsession = dbsession

            logging.getLogger().info(
                f"Got message of type {msg.type} from {req_ctxt.source} \n Message: {msg} \n"
            )

            # get handler
            msg_handler = getattr(self, "handle_" + msg.type, None)

            if not msg_handler:
                logging.getLogger().error(f"no handler defined for {msg.type}")
                return

            response = msg_handler(msg)

        return response