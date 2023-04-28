# FM SETUP INSTRUCTIONS #

# Index #
1. [Setup FM with push_fm script](#setup-fm-with-push_fm-script)
2. [Setup FM by copying built docker images](#setup-fm-by-copying-built-docker-images)
3. [Start/Restart FM](#start-or-restart-fm)
4. [Run FM Simulator](#run-fm-simulator)
5. [Setup sherpas](#setup-sherpas)
6. [Setup plugin](#setup-plugin)
7. [Setup optimal dispatch config](#setup-optimal-dispatch-config)
8. [Push mule docker image to local docker registry](#push-mule-docker-image-to-local-docker-registry)
9. [Fleet maintenance](#fleet-maintenance)
10. [Flash Summon button firmware](#flash-summon-button-firmware)
11. [Use saved routes](#use-saved-routes)

# FM Installation #

## FM installation prerequisites ##
1. Install docker(https://docs.docker.com/engine/install/)
2. Install docker-compose(https://www.digitalocean.com/community/tutorials/how-to-install-and-use-docker-compose-on-ubuntu-20-04)

## Setup FM with push_fm script ##
1. Clone fleet manager repository and setup git config for submodule 

    ```markdown
    git clone https://github.com/AtiMotors/fleet_manager
    cd fleet_manager
    git pull
    git submodule init
    
    # open and edit .git/config file, add branch=dev to submodule mule entry
    [submodule "mule"]
    url = https://<token>@github.com/AtiMotors/mule.git
    active = true
    branch = dev
    ```
    git submodule update  

2.  Checkout to release/branch, update mule submodule.
    ```markdown
    git checkout <branch>
    git submodule update --remote [Optional]
    git submodule update 
    ```

3. Setup cert files - You will need python installed in your machine to carry out this step

    3.1 *Update all_server_ips, http_scheme in static/fleet_config/fleet_config.toml, add wireguard ip of the server as well if wg access is present*
    ```markdown
    for example:
        all_server_ips=["192.168.6.11", "10.9.0.168", "127.0.0.1"]
        http_scheme="https"
    ```

    3.2 *Install toml, crytography in your machine(not server)- these packages are required to generate cert files*
    ```markdown
    pip install toml cryptography
    ```

    3.3 *Upon successful installation of the above mentioned packages, run setup_certs.py to generate FM cert file*
   ```markdown
   cd utils && python3 setup_certs.py ../static/fleet_config/fleet_config.toml ../static
   ```

   3.4 *Copy the cert file(static/certs/fm_rev_proxy_cert.pem) to all the sherpas(/opt/ati/config/fm_rev_proxy_cert.pem)*

4. Update static directory with map_files

    4.1. *Create map folders for each of the fleets*

    ```markdown
    mkdir static/fleet_1/map/
    copy all the map files of fleet_1 to static/fleet_1/map/

    mkdir static/fleet_2/map/
    copy all the map files of fleet_2 to static/fleet_2/map/
    ```  

5. If server has internet, allows you to download open-source packages (Recommended to use step 6 instead of this step)

    a. If you want to setup fm on a remote location, run push_fm script to create all the docker images on the server
    ```markdown
    ./scripts/push_fm.sh -Wi username@ip
     ```

    b. If you want to setup fm on your machine, run push_fm script to create all the docker images on your machine
    ```markdown
    ./scripts/push_fm.sh -W
     ```

6. If server doesn't have internet access, copy built docker images to the server from Ati server(data@192.168.10.21:/atidata/datasets/FM_v<fm_version>_docker_images), run the following commands

    a. Load base images on server/localhost
    ```markdown
    ssh username@ip
    cd FM_v<fm_version>_docker_images
    bash load_docker_images.sh
    exit
    ```

    b. If you want to setup fm on a remote location, run push_fm script from your machine to create all the docker images on the server
    ```markdown
    ./scripts/push_fm.sh -Wbi username@ip
     ```

    c. If you want to setup fm on your machine, run push_fm script from your machine to create all the docker images on your machine
    ```markdown
    ./scripts/push_fm.sh -Wb

7. [Setup plugins](#setup-plugin) if any.

8. [Setup sherpas](#setup-sherpas).

9. [Setup optimal dispatch config](#setup-optimal-dispatch-config)

10. [Push mule docker image to local docker registry](#push-mule-docker-image-to-local-docker-registry)

11. To start using fleet_manager, follow [Start or Restart FM](#start-or-restart-fm)


# Setup FM by copying built docker images #

1. Copy built docker images to the FM server from Ati server(data@192.168.10.21:/atidata/datasets/FM_v<fm_version>_docker_images) 

2. Load docker images 
```markdown
cd FM_v<fm_version>_docker_images
bash load_docker_images.sh
```

3. Backup the current fleet_config directory present in the FM server. Copy the updated fleet_config directory from FM_v<fm_version>_docker_images folder to the FM server static dir, update it with the info from fleet_config backup . With updates, config parameters change, redoing config will help.  Static dir should contain updated fleet_config, mule_config, certs, all the required map_folders etc.
    
4. Copy docker-compose.yml from <fm_repository>/misc/ or FM_v<fm_version>_docker_images folder to the static folder.

5. Create cert files if not already present by following [Setup FM with push_fm script](#setup-fm-with-push_fm-script) steps 1-3.

6. Copy the cert files generated (fm_rev_proxy_cert.pem, fm_rev_proxy_key.pem) to the static/certs/ directory in the FM server

7. Follow steps 7-10 in [Setup FM with push_fm script](#setup-fm-with-push_fm-script)

8. To start using fleet_manager, follow [Start or Restart FM](#start-or-restart-fm)


# Start or Restart FM #

   1. Modify timezone if required by setting environment variables TZ, PGTZ in services fleet_manager, db enlisted in static/docker-compose.yml.

   2. Start FM
   ```markdown
   cd static
   docker-compose -p fm down
   docker-compose -p fm up
   ```

   3. Use FM through UI, if running FM on localhost use ip as 127.0.0.1
   ```markdown
   https://<ip>/login
   username: <username>
   password: <password>
   ```

   4. Addition/Deletion of fleets, sherpas should be done through Configure page on the dashboard. Adding it to fleet_config.toml will have no effect. Fleets names have to be same as map_names. Copy the map files to the static directory on FM server by following [Setup FM with push_fm script](#setup-fm-with-push_fm-script) step 4 before trying to add it through dashboard.

   5. Please restart FM using restart_fleet_manager button on the maintenance page, after adding sherpas/fleets.  

   6. Induct all the sherpas that you want to use   
      a. Press enable for trips button from sherpa card   
      b. Only those sherpas that has been enabled for trips will get assigned with a trip 
    
   7. Follow [Fleet maintenance](#fleet-maintenance) if needs be 


# Run FM Simulator #
  a. Follow [Setup FM with push_fm script](#setup-fm-with-push_fm-script) , steps 1-2

  b. Set simulate in static/fleet_config/fleet_config.toml

  ```markdown
  [fleet.simulator]
  simulate=true
  ```

  c. To get trip bookings done automatically add routes(list of station names), trip booking frequency(seconds) to fleet_config.
  ```markdown
  [fleet.simulator.routes]
  route1 = [["Station A", "Station B"], [10]]
  route2 = [["Station A", "Station C"], [60]]
  ```

  d. Make sure all the stations mentioned in gmaj file(<fleet_name>/map/grid_map_attributes.json) has only the below mentioned tags. Tags like conveyor, auto_hitch, auto_unhitch will not work in simulator mode.
  ```markdown
   "station_tags": [
    "parking",
    "dispatch_not_reqd"
   ]
  ```

  e. If you want to start sherpas at particular station add this patch to config
  ```markdown
  [fleet.simulator.initialize_sherpas_at]
  sample_sherpa="Station A"
  ```

  f. If you want to simulate transit visas set visa handling in fleet.simulator config
  ```markdown
  [fleet.simulator]
  visa_handling=true 
  ```

  g.Follow remaining steps in [Setup FM with push_fm script](#setup-fm-with-push_fm-script), steps 3-7. 
  [Setup Sherpa](#setup-sherpas) not required for simulation


# Setup sherpas #

a. Copy fm cert file(fm_rev_proxy_cert.pem) generated in [Setup FM with push_fm script](#setup-fm-with-push_fm-script) step 3 to sherpa's /opt/ati/config directory

b. Add this patch to /opt/ati/config/config.toml in the mule
```markdown
[fleet]
api_key = " "
chassis_number = " "
data_url = "https://<fm_ip_address>:443/api/static"
http_url = "https://<fm_ip_address>:443"
ws_url = "wss://<fm_ip_address>:443/ws/api/v1/sherpa/"
fm_cert_file="/app/config/fm_rev_proxy_cert.pem"
```

# Setup Plugin #
a. [Setup IES](#setup-ies)

b. Summon button, conveyor plugins can be configured through UI (maintenance/Plugin Editor). Add the required plugins to static/fleet_config/plugin_config.toml. Restart would be required after you add a new plugin,post restart you would see a plugin editor page in UI.
```markdown
all_plugins=["summon_button", "conveyor"]
```

# Setup IES #
a. Add IES plugin to static/fleet_config/plugin_config.toml
```markdown
all_plugins=["ies"]
```

b. Modify static/plugin_ies/locationID_station_mapping.json file. Map IES station names to corresponding ati station names as the template indicates.
```markdown
{
    "Warehouse_Pick": "ECFA start",
    "HP02_FA02": "ECFA-2",
    "HP03_FA01": "ECFA-1",
}
```

# Setup optimal dispatch config #

Optimal dispatch logic tries to allocate the pending trips with the best sherpa available. Choice of best sherpa is made with the paramter $Z$

$Z=(eta)^a/(priority)^b$
<br>
$priority=p1/p2$

```markdown
where,
    eta - expected time of arrival computed for the sherpa to reach the first station of the trip booked,
    priority - measure of how long a trip has been pending,
    p1 - Time since booking of currrent trip, 
    p2 - Minimum of time since booking across all the pending trips,
    a - eta power factor , 0<a<1,
    b - priority power factor , 0<b<1,
```

1. **Maximise number of trips done**: To get maximum number of trips done in a given time frame eta_power_factor can be set to 1, priority_power_factor can be set to 0. This will make the optimal disaptch logic to lean towards trips that can be started faster. The trip booking order will not be followed.

```markdown
[optimal_dispatch]
method="hungarian"
prioritise_waiting_stations=true
eta_power_factor=1.0
priority_power_factor=0.0
```

2. **Fair scheduling**: To configure optimal dispatch logic to take trips in the order they were booked eta_power_factor can be set to 0, priority_power_factor can be set to 1.

```markdown
[optimal_dispatch]
method="hungarian"
prioritise_waiting_stations=true
eta_power_factor=0.0
priority_power_factor=1.0
```

3. **Custom configuration**: There is no ideal combination of eta_power_factor, priority_power_factor. They should be choosen according to the frequecy of trip bookings, route length between the stations to maximise the throughtput.

4. For good takt time, eta power factor should be higher, for fair scheduling priority power factor should be set higher.

5. Sherpas can also be restricted from running on certain routes/station by setting up exclude_stations. Check [saved route](#use-saved-routes) feature.
```

6. To reduce computation load due to optimal dispatch, max_trips_to_consider can be lowered. For a standalone/FM on sherpa, max_trips_to_consider can be set to a value less than 5 depending on the use case. Optimal dispatch logic will be run only for the first max_trips_to_consider number of trips. Default is set to 15.
```markdown
[optimal_dispatch]
max_trips_to_consider=15
```


 
# Push mule docker image to local docker registry #

1. Copy mule docker image tar file to fm_server and load the image 
```markdown
docker load -i <mule_image tar file>
```
2. Tag mule image with registry ip, tag on fm server
```markdown
docker tag mule:<mule_tag> <fm_ip>:443/mule:fm
```

3. Setup certs for docker push on fm server
```markdown 
sudo mkdir /etc/docker/certs.d/<fm_ip>:443
sudo cp <fm_static_dir>/certs/fm_rev_proxy_cert.pem /etc/docker/certs.d/<fm_ip>:443/domain.crt
```

4. Push mule docker image to FM local registry 
```markdown
# auth has been added to docker registry
docker login -u ati_sherpa -p atiCode112  <fm_ip>:443/mule:fm
docker push <fm_ip>:443/mule:fm
```

# Fleet maintenance # 

## Update map files ## 
1. Copy all the new map files to <fm_static_directory>/<fleet_name>/all_maps/<map_version_name>/ folder
2. Select the fleet which needs the map update from the webpage header in the dashboard and press update_map button on the webpage header(present along with start/stop fleet , emergency_stop fleet etc.), and choose map_version from drop down
3. Restart of FM after update map button is pressed. FM Pop up would ask for restart. 


## Swap sherpas between fleets ##
1. Delete the current sherpa entry and then again add it to a different fleet. Sherpa's can't be swapped directly. FM restart would be required post addition of sherpa to the new fleet.


## Generate api keys for sherpas/conveyor/summon_button/any hardware ##
1.  Run utils/api_key_gen.py in utils directory in fleet_manager - You will need fleet_manager repository access, python installed in your machine to run this. Python dependecies required: secrets, click 
```markdown
cd <path_to_fleet_manager_repository>/utils
python3 api_key_gen.py --hw_id <unique_hwid>
```

2. To generate api keys for n devices like summon_button
```markdown
cd <path_to_fleet_manager_repository>/utils
python3 utils/gen_api_keys_n_devices.py --num_devices 10 
```


## Add/Remove frontendusers ##
1. Run utils/gen_hashed_password.py in utils directory in fleet_manager - You will need fleet_manager repository access, python installed in your machine to run this. Python dependecies required: hashlib, click
```markdown
cd <path_to_fleet_manager_repository>/utils
python3 utils/gen_hashed_password.py --password <password>
```

2. The generated hasshed password can be added to <fm_static_directory>/fleet_config/frontend_users.toml
```markdown
[frontenduser.<new_user>]
hashed_password=<hashed password>
```

3. Remove unwanted entries from <fm_static_directory>/fleet_config/frontend_users.toml if any, restart FM for the changes to take effect.

4. Default FM login credentials
```markdown
username: ati_support 
password: atiSupport112 
role: support

username: admin 
password: 1234
role: support

username: supervisor 
password: ati1234
role: supervisor

username: operator 
password: 1234
role: operator
```

# Flash summon button firmware #

a. Connect summon button to your laptop via USB to flash firmware

b. Copy FlashTool_v2.3.6 from data@192.168.10.21:/atidata/datasets/FM_v<fm_version>_docker_images> to your laptop, run the same. 
```markdown 
cd FlashTool_v2.3.6
sudo bash ./install.sh
sudo bash ./flashtool_8mb.sh 
```
c. Upon flashing, reconnect the summon button usb. 

d. Generate unique api key for summon button by using following generate api keys section in [Fleet Maintenance](#fleet-maintenance)

e. Press and hold the button until LED turns blue, connect to summon button via wifi. For instance you would see something like Summon_192049 in the available/known wifi networks. Upon successful connection to summon button wifi, you will see a summon button UI.

f. Press configure WiFi, choose the preferred network and add the wifi password for the same, save it. Wait unitl summon button led turns from yellow to blinking red .

g. Repeat step e, connect to summon button network

h. Now press configure device, add FM plugin url to HOST. PLUGIN_PORT by default would be 8002
```markdown 
ws://<FM_IP>:<PLUGIN_PORT>/plugin/ws/api/v1/summon_button
```

i. Set wifi type: WPA/WPA2

j. Set Mode to WiFi-Only

k. Set HEARTBEAT to disable

l. Set APIKEY using api key generated in step d , save.
```markdown
X-API-Key:<api_key>
```
m. Press restart device in summon button UI.

# Use Saved routes #

1. Enable battery swap trips:

a. Set up conditional trip config
```markdown
[conditional_trips]
trip_types = ["battery_swap"]

[conditional_trips.battery_swap]
book=true
max_trips = 2 # max number of sherpas that can be sent for battery swap at the same time
threshold = 100 # battery level
priority = 10  # trip priority
```
b. Select the route you want the sherpa to do when battery level is below threshold, save it as battery_swap_<fleet_name> in book new trips page.

2. Enable idling trips:

a. Set up conditional trip config
```markdown
[conditional_trips]
trip_types = ["idling_sherpa"]

[conditional_trips.idling_sherpa]
book=true
max_trips = 2 # max number of sherpas that can be booked with trips when found idling at the same time 
threshold = 100 # battery level
priority = 1  # trip priority
```
b. Select the route you want the sherpa to do when is found idling, save it as idling_<fleet_name> in book new trips page.

3. Disable sherpa from going to a list of stations

a. Select the list of stations you want the sherpa to not go to, save it as exclude_stations_<sherpa_name> in book new trips page.







