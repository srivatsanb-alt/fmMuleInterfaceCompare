#!/bin/sh
set -e
export VEHICLE_TYPE=$1
echo "flash_v2.sh: flashing vehicle type '$VEHICLE_TYPE'"
docker cp mule:/app/ati/tools/uniflash/delfino_image .
echo "copying delfino images"
echo mule:/app/ati/tools/uniflash/delfino_image/delfino_firmware_$VEHICLE_TYPE.out
docker cp mule:/app/ati/tools/uniflash/delfino_image/delfino_firmware_$VEHICLE_TYPE.out ti/
docker run \
	--net host \
	-t \
	-v $(pwd)/libpython2.7.so.1.0:/usr/lib/libpython2.7.so.1.0:ro \
	-v $(pwd)/ti:/ti \
	-v $(pwd)/qemu-x86_64:/usr/bin/qemu-x86_64-static:ro \
	--privileged \
	--rm \
	amd64/ubuntu:18.04 \
	bash -c "cd ti && ./program_v2.sh $VEHICLE_TYPE"
