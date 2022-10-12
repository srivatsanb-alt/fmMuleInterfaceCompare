#!/bin/bash
set -e

TAG="latest"
MULE_USER_NAME="ati"
VEHICLE_TYPE="tug"

###### DELETE later
# export FM_SERVER_IP="192.168.6.11"
# export DOCKER_REGISTRY_PORT=443
# export PGTZ="Asia/Kolkata"

Help()
{
  # Display Help
  echo "Program to push fleet_manager repo to the FM server!"
  echo
  echo "Args: [-n/h]"
  echo "options:"
  echo "n     Name of the mule. ex: tug-43"
  echo "t     Tag name of mule image. default is \"latest\""
  echo "u     Host-name of the vehicle. default is \"ati\""
  echo "v     Vehicle type. default is \"tug\""
  echo "h     Display help"
}

# Get the options
while getopts n:t:u:v:h flag
do
  case "${flag}" in
    h) # display Help
      Help
      exit;;
    n) # input IP_ADDRESS
      MULE_NAME=${OPTARG}
      echo "MULE_NAME $MULE_NAME";;
    t) # input tag name of mule image
      TAG=${OPTARG}
      echo "TAG $TAG";;
    u) # input linux user name on the vehicle
      MULE_USER_NAME=${OPTARG}
      echo "MULE_USER_NAME $MULE_USER_NAME";;
    v) # VEHICLE_TYPE
      VEHICLE_TYPE=${OPTARG}
      echo "VEHICLE_TYPE $VEHICLE_TYPE";;
    ?/) # Invalid option
      echo "Error: Invalid option"
      exit;;
  esac
done

echo "Checking docker image ID on mule $MULE_NAME from with that on $FM_SERVER_IP!!"
id_fm=$(docker images --format {{.ID}} localhost:5000/ubuntu)
echo "Docker image ID on $FM_SERVER_IP $id_fm!!"
id_mule=$(ssh $MULE_USER_NAME@$MULE_NAME.local docker images --format {{.ID}} mule)
echo "Docker image ID on $MULE_USER_NAME $id_mule!!"


if [ $id_fm = $id_mule ]; then
  echo "Mule has the right image! No need to update!!"
else
  echo "Starting the docker image push process!!"
  echo "killing mule docker!!"
  ssh $MULE_USER_NAME@"$MULE_NAME.local" docker stop mule
  echo "Pushing domain.crt files to mule $MULE_NAME from $FM_SERVER_IP!!"
  ssh $MULE_USER_NAME@"$MULE_NAME.local" sudo mkdir -p /etc/docker/certs.d/"$FM_SERVER_IP:$DOCKER_REGISTRY_PORT"
  rsync ~/certs/domain.crt $MULE_USER_NAME@"$MULE_NAME.local":.
  ssh $MULE_USER_NAME@"$MULE_NAME.local" sudo rsync ~/domain.crt /etc/docker/certs.d/"$FM_SERVER_IP:$DOCKER_REGISTRY_PORT"/ca.crt
  echo "Pushing docker image ubuntu:$TAG to mule $MULE_NAME from $FM_SERVER_IP:$DOCKER_REGISTRY_PORT!!"
  export DOCKER_HOST=ssh://ati@$MULE_NAME.local
  docker pull $FM_SERVER_IP:$DOCKER_REGISTRY_PORT/mule:$TAG
  # Stop the container if it's already running
  docker stop mule || true
  docker rm mule || true

  DEVICES=
  DEVICES+=" --device /dev/delphino"
  DEVICES+=" --device /dev/ati_indicators"
  DEVICES+=" --device /dev/ati_epo"
  DEVICES+=" --device /dev/ati_power"
  DEVICES+=" --device /dev/snd"
  DEVICES+=" --device /dev/video0"
  DEVICES+=" --device /dev/video1"
  DEVICES+=" --device /dev/video2"
  if [[ $VEHICLE_TYPE == "lite" ]]; then
    DEVICES+=" --device /dev/video3"
    DEVICES+=" --device /dev/video4"
    DEVICES+=" --device /dev/video5"
    echo "Pushing to sherpa '$VEHICLE_TYPE'. Adding rear camera devices"
  else
    echo "Pushing to sherpa '$VEHICLE_TYPE'."
  fi
  DEVICES+=" --device /dev/video10"
  DEVICES+=" --device /dev/video11"
  DEVICES+=" --device /dev/video12"
  DEVICES+=" --device /dev/video13"

  # FIXME: We shouldn't be hardcoding TZ
  # We need NET_ADMIN and host for BLE
  docker run -d \
      --restart=always \
      --user 1000:1000 \
      --group-add dialout --group-add video --group-add audio --group-add bluetooth \
      --net host --cap-add NET_ADMIN \
      --name mule \
      --runtime nvidia \
      ${DEVICES} \
      -e TZ=$PGTZ \
      -v /opt/ati/data:/data \
      -v /opt/ati/ref-data:/ref-data \
      -v /opt/ati/models:/models \
      -v /opt/ati/config:/app/config \
      -v /opt/ati/run:/app/out \
      -v /var/run/dbus/system_bus_socket:/var/run/dbus/system_bus_socket \
      $FM_SERVER_IP:$DOCKER_REGISTRY_PORT/mule:$TAG
fi
