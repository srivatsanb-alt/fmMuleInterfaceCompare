# Setup FM on windows #
1. Copy the folder containing all the required docker images from data@192.168.10.21:/atidata/datasets/FM_v<fm_version>_docker_images to the on windows server

2. Make sure docker software is installed and running. Make sure docker-compose is installed.


3. Load the docker images
```markdown
ssh to windows server
cd FM_v<fm_version>_docker_images
bash load_docker_images.sh
```

4. Download nginx-1.23.3 setup files from http://nginx.org/en/download.html and install it on the windows server. Install it and make sure nginx.conf can be modified. Based on the installation path is common to all the users permission might be restricted.

5. Generate certs file by following step 1-3 of "Setup FM with push_fm script" from readme.pdf

6. Copy static folder from FM repo to the windows server

7. Copy misc/docker-compose_windows.yml as docker-compose.yml to the static folder on the windows server

8. Copy misc/nginx_windows.conf as nginx.conf, static/certs/fm_rev_proxy_cert.pem, static/certs/fm_rev_proxy_cert.pem to <nginx_installation_path>/conf/ on the windows server

9. Copy all the contents from dashboard folder in fleet_manager repository to <nginx_installation_path>/html on the windows server

10. Run nginx.exe

11. cd static, run docker-compose -p fm up
