#!/bin/bash
set -e

source ./scripts/push_utils.sh

clean_static_dir=0
copy_static=1
server=0
build_base=1

# Set variables
IP_ADDRESS="localhost"
NETWORK_TYPE="wlp"
FM_SERVER_USERNAME="ati"
FM_PORT=8001
PLUGIN_PORT=8002
REDIS_PORT=6379

# Get the options
while getopts i:hcWbv flag;
do
  case "${flag}" in
    h) # display Help
      Help
      exit;;
    c) # clean dirty directory, static
      clean_static_dir=1;;
    W) # WILL NOT copy from the remote folder
      copy_static=0;;
    i) # input IP_ADDRESS
      IP_ADDRESS=$OPTARG
      echo $IP_ADDRESS;server=1;;
    b) # WILL NOT create base image
      build_base=0;;
    ?/) # Invalid option
      echo "Error: Invalid option"
      exit;;
  esac
done

if [ $server == 1 ]; then
  export DOCKER_HOST=ssh://$IP_ADDRESS
  FM_SERVER_USERNAME=`echo $IP_ADDRESS | cut -d@ -f1`
  FM_SERVER_IP=`echo $IP_ADDRESS | cut -d@ -f2`
  echo "DOCKER_HOST $DOCKER_HOST"
else
  FM_SERVER_USERNAME=$USER
  FM_SERVER_IP=$(get_localhost_ip $IP_ADDRESS $NETWORK_TYPE)
fi

printf "\n \n \n"
read -p "Pls confirm the above IP_ADDRESS is right? (Correct/Cancel). Cancel if not sure! " RESP
if [ "$RESP" = "Correct" ]; then
  echo "Preparing to push docker to $IP_ADDRESS"
else
  echo "Incorrect response. Will stop this push process. Try again!"
  exit
fi

if [[ $copy_static == 1 ]] && [[ $server == 1 ]] ; then
{
  printf "\n \n \n"

  if rsync -azP --no-o --no-g --no-perms $IP_ADDRESS:static/certs static/ ; then
  {
      echo "Copied certs dir from FM server successfully"
  }
  else
  {
      echo "Unable to copy certs dir from FM server"
      exit
  }
  fi

}
else
{
  printf "\n \n \n"
  echo "You chose NOT TO copy static folder from FM server!"
  read -p "Are you sure you want to continue? (I Am SuRe/Cancel). Cancel if not sure! " RESP
  if [ "$RESP" = "I Am SuRe" ]; then
    echo "Pushing to $IP_ADDRESS"
  else
    echo "Incorrect response. Will stop this push process. Try again!"
    exit;
  fi
}
fi

if [ $server == 1 ] ; then
  create_static_backup $IP_ADDRESS # function defined in push_utils
else
  cp misc/docker_compose_host.yml static/
fi


BRANCH=$(git rev-parse --abbrev-ref HEAD)
GIT_COMMIT="$(git rev-parse HEAD)"
GIT_TAG=$(git describe --all | awk '{split($0,a,"/"); print a[2];}')
IS_DIRTY="$(git diff --quiet || echo 'dirty')"
FM_IMAGE_INFO="FM image built on $USER@$(hostname) branch $BRANCH $GIT_COMMIT (tags $GIT_TAG) IS_DIRTY $IS_DIRTY $(date)"


echo "FM_IMAGE_INFO: $FM_IMAGE_INFO"

echo "Building fleet manager docker image"
if [ $build_base == 1 ] ; then
{
  echo "Will build base image!"
  docker image build -t fleet_manager_base:dev -f docker_files/Dockerfile.base .
  cd fm_plugins && bash scripts/build_base_image.sh
  cd ../
  docker pull nginx:1.23.3
  docker pull postgres:14.0
  docker pull grafana/grafana:9.5.2
  docker pull registry:2   
}
else
{
  echo "Skipping base image build step!"
}
fi

conf_file="nginx_host.conf"
docker image build --build-arg CONF="${conf_file}" -t fm_nginx:1.23.3 -f docker_files/nginx.Dockerfile .

echo "Successfully built nginx image"
MULE_IMAGE_ID=$(docker images --format {{.ID}} localhost:$DOCKER_REGISTRY_PORT/mule)
echo "MULE_IMAGE_ID $MULE_IMAGE_ID"

docker image build --build-arg FM_IMAGE_INFO="${FM_IMAGE_INFO}" \
                   --build-arg FM_TAG="${GIT_TAG}" \
	           --build-arg MULE_IMAGE_ID="${MULE_IMAGE_ID}" \
		   --build-arg FM_SERVER_USERNAME="${FM_SERVER_USERNAME}" \
		   --build-arg FM_PORT="${FM_PORT}" \
		   --build-arg REDIS_PORT="${REDIS_PORT}" \
		   --build-arg PLUGIN_PORT="${PLUGIN_PORT}" \
		   -t fleet_manager:dev -f docker_files/Dockerfile .

FM_IMAGE_ID=$(docker images --format {{.ID}} fleet_manager:dev)
echo "Successfully built FM Image $FM_IMAGE_ID!"

docker image build -t fm_grafana:9.5.2 -f docker_files/grafana.Dockerfile .
echo "Successfully built grafana Image"


cd fm_plugins && bash scripts/build_final_image.sh
cd ../
echo "Built plugin docker images successfully"

if [ $clean_static_dir == 1 ] ; then
{
  echo "Restoring the directory \"static\" to its clean state! "
  clean_static
}
else
{
  echo "Pls note that the directory \"static\" is modified and hence your repo is not \"clean\" now! "
}
fi
