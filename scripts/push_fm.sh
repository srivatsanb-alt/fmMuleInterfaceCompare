#!/bin/bash
set -e

source ./scripts/push_utils.sh

clean_static_dir=0
copy_static=1
clear_db=0
server=0

# Set variables
IP_ADDRESS="localhost"

# Get the options
while getopts "i:hcWD" option; do
  case $option in
    h) # display Help
      Help
      exit;;
    c) # clean dirty directory, static
      clean_static_dir=1;;
    W) # WILL NOT copy from the remote folder
      copy_static=0;;
    D) # Will clear existing db tables
      clear_db=1;;
    i) # Enter a name
      IP_ADDRESS=$OPTARG
      echo $IP_ADDRESS;server=1;;
    ?/) # Invalid option
      echo "Error: Invalid option"
      exit;;
  esac
done

if [ $server == 1 ]; then
	export DOCKER_HOST=ssh://$IP_ADDRESS
	echo "DOCKER_HOST $DOCKER_HOST"
fi

read -p "Pls confirm the above IP_ADDRESS is right? (Correct/Cancel). Cancel if not sure! " RESP
if [ "$RESP" = "Correct" ]; then
  echo "Preparing to push docker to $IP_ADDRESS"
else
  echo "Incorrect response. Will stop this push process. Try again!"
  exit
fi

if [[ $copy_static == 1 ]] && [[ $server == 1 ]] ; then
{
  echo "Copying \"static\" folder from the FM server $DOCKER_HOST"
  {
	  rsync -azP $IP_ADDRESS:static/* static/.
  } || {
	  echo "couldn't find fleet_manager container, cannot copy static files"
  }
}
else
{
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
IMAGE_ID="Image built on $USER@$(hostname)_from $GIT_TAG branch $BRANCH_$(date)"
echo "IMAGE_ID: $IMAGE_ID"

echo "Building fleet manager docker image"
docker image build --build-arg IMAGE_ID="${IMAGE_ID}" -t fleet_manager_base:dev -f Dockerfile.base .
docker image build --build-arg IMAGE_ID="${IMAGE_ID}" -t fleet_manager:dev -f Dockerfile .

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
