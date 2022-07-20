from datetime import datetime


TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def ts_to_str(ts):
    return (datetime.strftime(datetime.fromtimestamp(ts), TIME_FORMAT),)
