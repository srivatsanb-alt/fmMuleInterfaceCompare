#!/bin/bash
set -e
GIT_COMMIT="$(git rev-parse HEAD)"
GIT_DES=$(git describe --all)
GIT_TAG=$(git describe --all | awk '{split($0,a,"/"); print a[2];}')
GIT_DES=$(git describe --all)
IS_DIRTY="$(git diff --quiet || echo 'dirty')"
LAST_COMMIT_DT="$(git log -1 --format=%cd)"
if [[ $GIT_DES =~ "tags/" ]] ; then
   FM_VERSION=$GIT_TAG
   GIT_TAGGED="True"
else
   FM_VERSION=$(git rev-parse --abbrev-ref HEAD)
fi
FM_IMAGE_INFO="FM image built on $USER@$(hostname), FM_VERSION: $FM_VERSION (des: $GIT_DES $IS_DIRTY) $LAST_COMMIT_DT)"

build_base_images_interactive()
{
   read -p "Should build base images? (y/n) - " build_base_images
   if [ "$build_base_images" = "y" ]; then 
   {
        build_base_images 
   }
   else
   {
       echo "Not building base images"
   }
   fi
}

build_base_images() 
{
   echo "Will build base image!"
   docker image build -t fleet_manager_base:dev -f docker_files/Dockerfile.base .
   cd fm_plugins && bash scripts/build_base_image.sh dev
   cd ../
   docker pull nginx:1.23.3
   docker pull mongo-express:1.0.0-alpha
   docker pull mongo:7.0
   docker pull postgres:14.0
   docker pull registry:2
   docker pull redis:latest
}


build_final_images() 
{
   conf_file="nginx_bridge.conf"
   docker image build --build-arg CONF="${conf_file}" -t fm_nginx:$FM_VERSION -f docker_files/nginx.Dockerfile .
   docker image build --build-arg FM_IMAGE_INFO="${FM_IMAGE_INFO}" \
                      --build-arg FM_TAG="${GIT_TAG}" \
		      --build-arg GIT_TAGGED="${GIT_TAGGED}" \
		      --build-arg LAST_COMMIT_DT="${LAST_COMMIT_DT}" \
		      -t fleet_manager:$FM_VERSION -f docker_files/Dockerfile .


   cd fm_plugins && bash scripts/build_final_image.sh $FM_VERSION
   cd ../
   echo "Built plugin docker images successfully"

   # set fm version in docker_compose file
   mkdir -p static
   cp misc/docker_compose_untagged.yml static/docker_compose_v$FM_VERSION.yml 
    
   if [ "$(uname)" = "Darwin" ]; then
   {
     sed -i.bak "s/fm_version/$FM_VERSION/g" static/docker_compose_v$FM_VERSION.yml
   }
   else {
     sed -i "s/fm_version/$FM_VERSION/g" static/docker_compose_v$FM_VERSION.yml
   }
   fi
}


