#!/bin/bash
set -e

clean_repo=0
copy_static=1

Help()
{
  # Display Help
  echo "Program to push fleet_manager repo to the FM server!"
  echo
  echo "Args: [-i/W|c|h]"
  echo "options:"
  echo "i     Give IP address of the FM server, default is localhost"
  echo "W     WILL NOT copy the static files from the FM server. Copies the contents of static folder on local machine directly to the FM server."
  echo "c     Checksout the local directory static to its current git commit after the push is successful"
  echo "h     Display help"
}

clean_static()
{
  rm -r static
  git checkout static
}

# Set variables
IP_ADDRESS="localhost"

# Get the options
while getopts "hi:c" option; do
  case $option in
    h) # display Help
      Help
      exit;;
    i) # Enter a name
      IP_ADDRESS=$OPTARG
      echo $IP_ADDRESS;;
    c) # clean dirty directory, static
      clean_repo=1;;
    W) # WILL NOT copy from the remote folder
      copy_static=0;;
    ?/) # Invalid option
      echo "Error: Invalid option"
      exit;;
  esac
done

export DOCKER_HOST=ssh://ati@$IP_ADDRESS
read -p "Pls confirm the above IP_ADDRESS is right? (Correct/Cancel). Cancel if not sure! " RESP
if [ "$RESP" = "Correct" ]; then
  echo "Preparing to push docker to $IP_ADDRESS"
else
  echo "Incorrect response. Will stop this push process. Try again!"
  exit
fi

if [ $copy_static ] ; then
{
  echo "Copying static folder enmasse from the FM docker container in server $DOCKER_HOST"
  docker cp fleet_manager:/app/static .
}
else
{
  echo "You chose NOT TO copy static folder from fm docker container!"
  read -p "Are you sure you want to continue? (I Am SuRe/Cancel). Cancel if not sure! " RESP
  if [ "$RESP" = "I Am SuRe" ]; then
    echo "Pushing to $IP_ADDRESS"
  else
    echo "Incorrect response. Will stop this push process. Try again!"
    exit;
  fi
}
fi

BRANCH=$(git rev-parse --abbrev-ref HEAD)
GIT_TAG="$(git rev-parse HEAD) $(git diff --quiet || echo 'dirty')"
IMAGE_ID="Image built on $USER@$(hostname)_from $GIT_TAG branch $BRANCH_$(date)"
echo "IMAGE_ID: $IMAGE_ID"

echo "Building fleet manager docker image"
docker image build --build-arg IMAGE_ID="${IMAGE_ID}" -t fleet_manager_base -f Dockerfile.base .
docker image build --build-arg IMAGE_ID="${IMAGE_ID}" -t fleet_manager -f Dockerfile .

if [ $clean_repo ] ; then
{
  clean_static
}
fi
