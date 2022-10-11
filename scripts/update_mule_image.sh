#!/bin/bash
set -e

TAG="latest"
MULE_USER_NAME="ati"

###### DELETE later
export FM_SERVER_IP="192.168.6.11"
export DOCKER_REGISTRY_PORT=5000

Help()
{
  # Display Help
  echo "Program to push fleet_manager repo to the FM server!"
  echo
  echo "Args: [-n/h]"
  echo "options:"
  echo "n     Name of the mule. ex: tug-43"
  echo "t     input tag name of mule image. default is \"latest\""
  echo "u     input linux user name on the vehicle. default is \"ati\""
  echo "h     Display help"
}

# Get the options
while getopts n:t:h flag
do
  case "${flag}" in
    h) # display Help
      Help
      exit;;
    n) # input IP_ADDRESS
      MULE_NAME=${OPTARG}
      echo $MULE_NAME;;
    t) # input tag name of mule image
      TAG=${OPTARG}
      echo $TAG;;
    u) # input linux user name on the vehicle
      MULE_USER_NAME=${OPTARG}
      echo $MULE_USER_NAME;;
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
  rsync ~/certs/domain.crt $MULE_USER_NAME@"$MULE_NAME.local":
  ssh $MULE_USER_NAME@"$MULE_NAME.local" sudo rsync /home/ati/domain.crt /etc/docker/certs.d/"$FM_SERVER_IP:$DOCKER_REGISTRY_PORT"/ca.crt
  echo "Pushing docker image ubuntu:$TAG to mule $MULE_NAME from $FM_SERVER_IP:$DOCKER_REGISTRY_PORT!!"
  ssh $MULE_USER_NAME@"$MULE_NAME.local" "docker pull $FM_SERVER_IP:$DOCKER_REGISTRY_PORT/mule:$TAG"
fi
