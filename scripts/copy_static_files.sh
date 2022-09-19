#!/bin/bash
set -e

clean_repo=0
copy_static=1

Help()
{
  # Display Help
  echo "Program to copy static files from the FM server to the directory \"static\" in the fleet_manager repo in the local machine!"
  echo
  echo "Args: [-i/|h]"
  echo "options:"
  echo "i     Give IP address of the FM server"
  echo "h     Display help"
}

clean_static()
{
  rm -r static
  git checkout static
}

# Get the options
while getopts "hi:c" option; do
  case $option in
    h) # display Help
      Help
      exit;;
    i) # Enter a name
      IP_ADDRESS=$OPTARG
      echo $IP_ADDRESS;;
    ?/) # Invalid option
      echo "Error: Invalid option"
      exit;;
  esac
done

export DOCKER_HOST=ssh://ati@$IP_ADDRESS
read -p "Pls confirm the above IP_ADDRESS is right? (Correct/Cancel). Cancel if not sure! " RESP
if [ "$RESP" = "Correct" ]; then
  echo "Copying static folder from fm docker container in server $DOCKER_HOST"
  docker cp fleet_manager:/app/static .
else
  echo "Will stop this push process. Try again!"
  exit
fi
