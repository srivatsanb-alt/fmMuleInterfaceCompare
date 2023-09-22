#!/bin/bash
set -e 
prod_release=$1 #y/n
master_fm_username=$2 
master_fm_password=$3

source scripts/build_fm_images.sh
source scripts/upload_images.sh

build_base_images
build_final_images

upload_to_sanjaya $prod_release $master_fm_username $master_fm_password
