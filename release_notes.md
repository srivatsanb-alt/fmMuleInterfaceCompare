# FM_v1.2.1 release notes #

# Index #
1. Install FM
2. Start/Restart FM
3. Run FM Simulator
4. Modify mule config
5. Known issues
6. Dashboard release 

# FM Installation #

## FM installation prerequisites ##
1. Install docker 
2. Install docker-compose 

## Setup FM ##
1. Clone fleet manager repository, 

    ```markdown
    git clone https://github.com/AtiMotors/fleet_manager
    cd fleet_manager
    git pull
    git submodule update --init --recursive
    ```

2.  Checkout to release FM_v1.2.1, update mule submodule.
    ```markdown
    git checkout FM_v1.2.1
    git submodule update --recursive
    ```

3. Update static directory with map_files, sherpa_details  
    
    3.1 *Add fleet names, customer details, server_ip to the static/fleet_config/fleet_config.toml*
    
    ```markdown
    server_ip="xyz"
    fleet_names=["sample_fleet", "sample_fleet_1"]
    customer="xyz"
    site="xyz"
    location="xyz"
    ```  

    3.2. *Add sherpa details of all the sherpas to the fleet_config following the sample given below- make sure sherpa names match hostname in the mule*

    ```markdown
    [fleet_sherpas.<sherpa_name>]
    hwid="abc"
    api_key="qZhoteD9zOHn_wBoYW04vgeaiLSBIoWP_jaVy5TQLp0_T30-789PAI"
    fleet_name="sample_fleet"

    [fleet_sherpas.<sherpa_name>]
    hwid="xyz"
    api_key="ffZhoteD9zOHn_wBoYW04vgeaiLSBIoWP_jaVy5TQLp0_T30-789PAI"
    fleet_name="sample_fleet_1"
    ```

    3.3. *Create map folders, map_files.txt for all the fleet names present in fleet_config.toml. Make sure grid_map_attributes.json is present*

    ```markdown
    mkdir sample_fleet/map/
    copy all the map files to sample_fleet/map/
    cd sample_fleet/map/
    ls > map_files.txt
    ```  

4. If server has internet, allows you to download open-source packages

    a. Push to server
    ```markdown
    ./scripts/push_fm.sh -WDi username@ip
     ```
    
    b. Push to localhost
    ```markdown
    ./scripts/push_fm.sh -WD
     ```

5. If server doesn't have internet access, copy built docker images to the server from Ati server(data@192.168.10.21:/atidata/datasets/FM_v1.2.1_docker_images), run the following commands
    

    a. Push to server
    ```markdown
    ssh username@ip 
    cd FM_v1.2.1_docker_images
    bash load_docker_images.sh
    cd fleet_manager
    ./scripts/push_fm.sh -WbDi username@ip
    ```

    b. Push to localhost
    ```markdown
    cd FM_v1.2.1_docker_images
    bash load_docker_images.sh
    cd fleet_manager
    ./scripts/push_fm.sh -WbD
    ```

# Start or Restart FM # 
   1. Clear DB - Only if required (Any map, station attribute changes/ Recovery from FM error/issue)
  
   ```markdown
   cd static
   bash clear_db.sh
   ```
   
   2. Restart FM
  
   ```markdown
   cd static
   docker-compose -p fm down
   docker-compose -p fm up
   ```
   
   3. Use FM through UI, if running FM on localhost use ip as 127.0.0.1
  
   ```markdown
   https://<ip>/login
   username: admin
   password: 1234
   ```

   4. Induct all the sherpas that you want to use   
      a. Press Induct to fleet button from sherpa card   
      b. Only those sherpas that has been inducted into fleet will get assigned with a trip   

# Run FM Simulator #
  a. Follow Setup FM, steps 1-2

  b. Set simulate in static/fleet_config/fleet_config.toml

  ```markdown
  simulate=true
  ```
  c. Set redis port in scripts/push_fm.sh
  ```markdown
  REDIS_PORT=6379
  ```
  d. Follow Setup FM, steps 3-5


# Modify mule config #

a. Add this patch to /opt/ati/config/config.toml in the mule
```markdown 
[fleet]
api_key = " "
chassis_number = " "
data_url = "http://<fm_ip_address>/api/static"
fm_ip = "http://<fm_ip_address>:8002"
ws_url = "ws://<fm_ip_address>:8002/ws/api/v1/sherpa/"
```

# Known Issues #

a. Trip analytics doesn't get created/updated for all the trip legs  
b. Trip management, sherpa status and events table in UI doesn't get updated without reload


# Dashboard release #

 [Dashboard release](https://docs.google.com/spreadsheets/d/1Vjvjt8A_gs-etPWFR7wpj5HJvfjHm1dk/edit#gid=828406457)







