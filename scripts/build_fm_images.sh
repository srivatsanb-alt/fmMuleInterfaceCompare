#!/bin/bash
set -e
BRANCH=$(git rev-parse --abbrev-ref HEAD)
GIT_COMMIT="$(git rev-parse HEAD)"
GIT_TAG=$(git describe --all | awk '{split($0,a,"/"); print a[2];}')
IS_DIRTY="$(git diff --quiet || echo 'dirty')"
FM_IMAGE_INFO="FM image built on $USER@$(hostname) branch $BRANCH $GIT_COMMIT (tags $GIT_TAG) IS_DIRTY $IS_DIRTY $(date)"
FM_VERSION=$GIT_TAG 


build_base_images() 
{
    read -p "Should build base images? (y/n) - " build_base_images
    if [ "$build_base_images" = "y" ]; then
    {
       echo "Will build base image!"
       docker image build -t fleet_manager_base:dev -f docker_files/Dockerfile.base .
       cd fm_plugins && bash scripts/build_base_image.sh dev
       cd ../
       docker pull nginx:1.23.3
       docker pull mongo-express:1.0.0-alpha
       docker pull mongo:7.0
       docker pull postgres:14.0
       docker pull grafana/grafana:9.5.2
       docker pull registry:2   
    }
    else
    {
       echo "Not building base images"
    }
    fi
}

build_final_images() 
{
   conf_file="nginx_bridge.conf"
   docker image build --build-arg CONF="${conf_file}" -t fm_nginx:$FM_VERSION -f docker_files/nginx.Dockerfile .
   docker image build --build-arg FM_IMAGE_INFO="${FM_IMAGE_INFO}" \
                      --build-arg FM_TAG="${GIT_TAG}" \
		      -t fleet_manager:$FM_VERSION -f docker_files/Dockerfile .

   docker image build -t fm_grafana:$FM_VERSION -f docker_files/grafana.Dockerfile .
   echo "Successfully built grafana Image"

   cd fm_plugins && bash scripts/build_final_image.sh $FM_VERSION
   cd ../
   echo "Built plugin docker images successfully"

   # set fm version in docker_compose file
   cp misc/docker_compose_untagged.yml static/docker_compose_v$FM_VERSION.yml 
   sed -i "s/fm_version/$FM_VERSION/g" static/docker_compose_v$FM_VERSION.yml
}


