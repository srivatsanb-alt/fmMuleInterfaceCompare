#!/bin/bash
set -e

TAG="latest"
MULE_USER_NAME="ati"

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

echo "Pushing docker image ubuntu:$TAG to mule $MULE_NAME from $FM_SERVER_IP:$DOCKER_REGISTRY_PORT!!"

ssh $MULE_USER_NAME@"$MULE_NAME.local" "docker pull $FM_SERVER_IP:$DOCKER_REGISTRY_PORT/mule:$TAG"
