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
12. [Setup master FM comms](#setup-master-fm-comms)
13. [Debug FM](#debug-fm)
14. [Config editor](#config-editor)

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

3. If you are using Linux, the FM software would work right away. If you are using MAC or windows -apply the diff run_docker_with_bridge_net.diff. This will ensure that the FM microservices run with docker bridge network. Plugins wouldn't work with bridge network
```
git apply run_docker_with_bridge_net.diff
```

4. Update static directory with map_files
    4.1. *Create map folders for each of the fleets*

    ```markdown
    mkdir static/fleet_1/map/
    copy all the map files of fleet_1 to static/fleet_1/map/

    mkdir static/fleet_2/map/
    copy all the map files of fleet_2 to static/fleet_2/map/
    ```  
5. Make sure default cert files were copied to the server. fm_rev_proxy_cert.pem, fm_rev_proxy_key.pem files have to be present. Create appropriate certs for the server post FM installation following step. The default certs files have been created with IP (127.0.0.1)
    ```
    ls static/certs
    ```

5. Check all the options available in push_fm script, use them according to your requirements
```
Program to push fleet_manager repo to the FM server!
Args: [-i/W|c|h]
options:
i     Give IP address of the FM server, default is localhost
W     Copies the contents of static folder on local machine directly to the FM server, else the static folder on server will be retained
c     Checksout the local directory static to its current git commit after the push is successful
b     WILL NOT build the base image
h     Display help
```

6. Use built base images if possible, the built images will be updated to data@192.168.10.21:/atidata/datasets and master fm docker registry


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

3. Copy docker_compose_host.yml from <fm_repository>/misc/ or FM_v<fm_version>_docker_images folder to the static folder.

4. Follow steps 7-10 in [Setup FM with push_fm script](#setup-fm-with-push_fm-script)

5. To start using fleet_manager, follow [Start or Restart FM](#start-or-restart-fm)


# Start or Restart FM #

   1. Modify timezone if required by setting environment variables TZ, PGTZ in services fleet_manager, db enlisted in static/docker_compose_host.yml 


   2. Start FM
   ```markdown
   cd static
   docker-compose -p fm -f docker_compose_host.yml down
   docker-compose -p fm -f docker_compose_host.yml up
   ```

   3. Use FM through UI, if running FM on localhost use ip as 127.0.0.1
   ```markdown
   https://<ip>/fm/
   username: <username>
   password: <password>
   ```

   4. Please restart FM using restart_fleet_manager button on the maintenance page, after adding sherpas/fleets.  

   5. Induct all the sherpas that you want to use   
      a. Press enable for trips button from sherpa card   
      b. Only those sherpas that has been enabled for trips will get assigned with a trip 
    
   6. Follow [Fleet maintenance](#fleet-maintenance) if needs be 

   7. Create cert files if not already done
   ```
   docker exec -it fleet_manager bash 
   create_certs "127.0.0.1, 192.168.6.10, 10.9.0.168"
   ```


# Run FM Simulator #
  a. Follow [Setup FM with push_fm script](#setup-fm-with-push_fm-script) , steps 1-2

  b. Set simulate to true in https://fm_ip/config_editor/db/fm_config/simulator

  ```markdown
  [fleet.simulator]
  simulate=true
  ```

  c. To get trip bookings done automatically add routes(list of station names), trip booking frequency(seconds) to https://<fm_ip>/config_editor/db/fm_config/simulator. route1 will be a scheduled trip, route2 would be booked as a normal one time trip
  ```markdown
  [fleet.simulator.routes]
  route1 = [["Station A", "Station B"], ["10", "2023-05-31 15:00:00", "2023-05-31 16:00:00"]]
  route2 = [["Station B", "Station A"], ["-1", "", ""]]
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

a. Copy fm cert file(fm_rev_proxy_cert.pem) generated in [Start or Restart FM](#start-or-restart-fm)step 8 to sherpa's /opt/ati/config directory

b. Add this patch to /opt/ati/config/config.toml in the mule
```markdown
[fleet]
api_key = " "
chassis_number = " "
ip = <fm_ip_address>
port = <fm_port>
fm_cert_file="/app/config/fm_rev_proxy_cert.pem"
```

# Setup Plugin #
Plugins needs to be activated using config_editor 
1. Once the fm is up go to https://<fm_server_ip>/config_editor -> choose plugin_config -> choose the plugin you want to activate and set activate plugin to True. 


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
docker login -u ati_sherpa -p atiCode112  <fm_ip>:443
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
b. Go to route ops(maintenance) page, select the route you want the sherpa to do when battery level is below threshold, press save and tag it as battery_swap route.

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
b. Go to route ops(maintenance) page, select the route you want the sherpa is found idling beyond threshold seconds, press save, select sherpa from dropdown and tag it as parking route.

3. Disable sherpa from going to a list of stations

a. Go to route ops(maintenance) page, select the stations that sherpa shouldn't go to, press save, select sherpa from dropdown and tag it as exclude_stations route.


# Setup master FM comms # 

1. Generate api key for the FM server 
```
cd <path_to_fleet_manager_repository>/utils
python3 api_key_gen.py --hw_id <customer_name>
```

2. Add customer to master_fm database 
```
1.Login to sanjaya.atimotors.com
2.Use add client functionality in client configuration page (requires customer name, api key generated in the previous step)
```

3. If the FM server has direct access to sanjaya.atimotors.com then make sure mfm_ip, port, cert_files are set as given below in https://<fm_ip>/config_editor/db/fm_config/master_fm
```
mfm_ip="sanjaya.atimotors.com"
mfm_port="443"
mfm_cert_file="/etc/ssl/certs/ca-certificates.crt"
http_scheme="https"
ws_scheme="wss"
```

4. If the FM server doesn't have direct access to sanjaya.atimotors.com but the FM server can be accessed via ssh then set mfm_ip, port, schemes are set as given below in https://<fm_ip>/config_editor/db/fm_config/master_fm. We will have to setup reverse tunnel to sanjaya.atimotors.com
```
mfm_ip="127.0.0.1"
mfm_port="9010"
mfm_cert_file="/etc/ssl/certs/ca-certificates.crt"
http_scheme="http"
ws_scheme="ws"
```

5. To setup reverse tunnel, copy the folder mfm_rev_tunnel from FM_v<fm_version>_docker_images to the machine which has access sanjaya.atimotors.com(pingable) and has ssh access to the FM server.
```
cd mfm_rev_tunnel
bash mfm_rev_tunnel.sh
```

4. Edit params in https://<fm_ip>/config_editor/db/fm_config/master_fm and restart the same
```
[master_fm.comms]
send_updates=true
ws_update_freq=60
update_freq=120
api_key=<api_key>
```

# Debug FM # 
1. Check if there were any queue build ups. The output would show queue build ups if any.
```
docker exec -it fleet_manager bash 
inspect
rqi
```

2. Check for occurences of rq errors (rqe) in fleet_manager.log, the output might lead to the issue
```
rqe
```

3. If you are unable to login to FM, Check the docker logs- this should be run outside docker. There might be some errors in the init scripts.
```
docker logs fleet_manager 
docker logs fleet_db
```

# Config editor # 

1. All the config can be accessed at https://<fm_ip>/config_editor/db/fm_config/master_fm

2. Credential can be found in docker-compose file 
```
 ME_CONFIG_BASICAUTH_USERNAME: "ati_support"
 ME_CONFIG_BASICAUTH_PASSWORD: "ati112"
```












