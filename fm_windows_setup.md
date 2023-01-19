# Setup FM on windows #
1. Copy the folder containing all the required docker images from data@192.168.10.21:/atidata/datasets/FM_v2.1_docker_images to the on windows server 


2. Load the docker images 
```markdown
ssh to windows server
cd FM_v2.1_docker_images
docker image load -i postgres_14_0.tar
docker image load -i registry_v2.tar
docker load -i fm_final_image_window.tar
```

3. Download nginx-1.14.2 setup files from http://nginx.org/en/download.html and install it on the windows server

4. From a machine which has access to FM repo checkout to head of fm_windows branch. 
```markdown
git pull
git checkout fm_windows
git submodule update
```

5. Update static/fleet_config/fleet_config.toml with all_server_ips (add the windows server ip to list all_server_ips)
```markdown
all_server_ips = ["192.168.6.10", "10.9.0.18", "127.0.01"]
```

6. Generate certs file by running the command below from fleet_manager repo
```markdown
cd utils && python3 setup_certs.py ../static/fleet_config/fleet_config.toml ../static 
```

5. Copy static folder from FM repo to the windows server 

6. Copy misc/docker-compose.yml to the static folder on the windows server

7. Copy misc/nginx.conf, static/certs/fm_rev_proxy_cert.pem, static/certs/fm_rev_proxy_cert.pem to <nginx_installation_path>/conf/ on the windows server

8. Copy all the contents from dashboard folder in fleet_manager repository to <nginx_installation_path>/html on the windows server

9. Run nginx.exe 

10. cd static, run docker-compose -p fm up