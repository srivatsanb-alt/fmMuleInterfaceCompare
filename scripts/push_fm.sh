#!/bin/bash
set -e

source ./scripts/push_utils.sh

clean_static_dir=0
copy_static=1
clear_db=0
server=0
build_base=1

# Set variables
IP_ADDRESS="localhost"
FM_SERVER_HOSTNAME="localhost"
DOCKER_REGISTRY_PORT=443

# Get the options
while getopts i:hcWDb flag;
do
  case "${flag}" in
    h) # display Help
      Help
      exit;;
    c) # clean dirty directory, static
      clean_static_dir=1;;
    W) # WILL NOT copy from the remote folder
      copy_static=0;;
    D) # Will clear existing db tables
      clear_db=1;;
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
  FM_SERVER_HOSTNAME=`echo $IP_ADDRESS | cut -d@ -f1`
	echo "DOCKER_HOST $DOCKER_HOST"
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
  echo "Copying \"static\" folder from the FM server $DOCKER_HOST"
  {
	  rsync -azP $IP_ADDRESS:static/* static/.
  } || {
	  echo "couldn't find fleet_manager container, cannot copy static files"
  }
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
fi

if [ $clear_db == 1 ] ; then
{
  echo "clear db $clear_db"
  clear_db_on_fm_server
}
fi

BRANCH=$(git rev-parse --abbrev-ref HEAD)
GIT_TAG="$(git rev-parse HEAD) $(git diff --quiet || echo 'dirty')"
FM_IMAGE_INFO="Image built on $USER@$(hostname)_from $GIT_TAG branch $BRANCH_$(date)"
echo "FM_IMAGE_INFO: $FM_IMAGE_INFO"

echo "Building fleet manager docker image"
if [ $build_base == 1 ] ; then
{
  echo "Will build base image!"
  docker image build -t fleet_manager_base:dev -f Dockerfile.base .
}
else
{
  echo "Skipping base image build step!"
}
fi


MULE_IMAGE_ID=$(docker images --format {{.ID}} localhost:$DOCKER_REGISTRY_PORT/mule)
echo "MULE_IMAGE_ID $MULE_IMAGE_ID"
docker image build --build-arg FM_IMAGE_INFO="${FM_IMAGE_INFO}" --build-arg MULE_IMAGE_ID="${MULE_IMAGE_ID}" --build-arg HOSTNAME="${FM_SERVER_HOSTNAME}" -t fleet_manager:dev -f Dockerfile .

FM_IMAGE_ID=$(docker images --format {{.ID}} fleet_manager:dev)
echo "Successfully built FM Image $FM_IMAGE_ID!"

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
