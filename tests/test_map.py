import os
from utils.router_utils import RouterModule
from models.db_session import DBSession
import sys

fleet_name = sys.argv[1]
map_path = os.path.join(os.environ["FM_STATIC_DIR"], f"{fleet_name}/map/")
rm = RouterModule(map_path)

with DBSession() as dbsession:
    fleet = dbsession.get_fleet(fleet_name)
    stations = dbsession.get_all_stations_of_fleet(fleet.id)
    station_len =len(stations)
    for i in range(station_len):
        for j in range(i+1, station_len):
            if stations[i].name != stations[j].name:
                print(rm.get_route_length(stations[i].pose, stations[j].pose))
    