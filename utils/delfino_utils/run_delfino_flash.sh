#!/bin/bash
set -e
export DOCKER_HOST=ssh://ati@$1
DOCKER_INFO=$(docker info 2>&1)
export VEHICLE_TYPE=$2
if [[ -z $VEHICLE_TYPE ]]; then
    echo "please specify vehicle type! tug  OR lite "
    echo "./flash_delfino.sh <mule address> <vehicle_type>"
    exit 1
fi
echo "Stopping docker container before flashing delfino firmware..."
docker stop mule || true
echo "Starting flash: Vehicle type '$VEHICLE_TYPE' IP: $1"
echo "..."
ssh ati@$1 'rsync -aP flash_v2.sh ../../opt/ati/uniflash'
ssh ati@$1 'rsync -aP program_v2.sh ../../opt/ati/uniflash/ti'
ssh ati@$1 "cd ../../opt/ati/uniflash && sudo bash flash_v2.sh $2"
echo "Completed flash!"
echo "Restarting docker container..."
docker restart mule || true
echo "Delfino firmware update complete!"
