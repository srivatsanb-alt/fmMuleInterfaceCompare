from plugins.plugin_comms import send_req_to_FM


def get_station_info(plugin_name, station_name):
    status_code, response_json = send_req_to_FM(
        plugin_name,
        "station_info",
        req_type="get",
        query=station_name,
    )
    return status_code, response_json
