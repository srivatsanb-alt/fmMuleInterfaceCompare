class HandlerConfiguration:
    def __init__(self):
        raise NotImplementedError("Config class cannot be instantiated")

    @classmethod
    def get_handler(cls, version="default"):

        if version == "default":
            from handlers.default.handlers import Handlers

            return Handlers()
        
        if version == "analytics":
            from handlers.default.analytics_handlers import AnalyticsHandler
            
            return AnalyticsHandler()
