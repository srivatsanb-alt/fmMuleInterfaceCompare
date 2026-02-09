#!/bin/bash
set -e
export VEHICLE_TYPE=$1
./dslite-C28xx_CPU1.sh -c TMS320F28379D.ccxml -e -fv delfino_firmware_$VEHICLE_TYPE.out -r 0
