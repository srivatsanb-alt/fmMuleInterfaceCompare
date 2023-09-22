#!/bin/bash
set -e 
source scripts/build_fm_images.sh
source scripts/upload_images.sh 

read -p "Want to build images on a remote server? (y/n) - " remote_server
if [ "$remote_server" = "y" ]; then
{
   read -p "Enter remote server ssh address: (like ati@x.x.x.x) - " remote_server_addr
   export DOCKER_HOST=ssh://$remote_server_addr
   echo "Have set docker host to $DOCKER_HOST"
}
fi

echo "FM Version: $FM_VERSION"

build_base_images_interactive
build_final_images 

copy_default_certs="n"
if [ "$remote_server" = "y" ]; then
{
   read -p "Enter static data folder path in the remote server (~/static) :  " static_data_path
   rsync -azvP static/docker_compose_v$FM_VERSION.yml $remote_server_addr:$static_data_path/.
   #rm static/docker_compose_v$FM_VERSION.yml
   ssh $remote_server_addr "ls -l $static_data_path/certs/fm_rev_proxy_cert.pem" || copy_default_certs="y"
   ssh $remote_server_addr "ls -l $static_data_path/certs/fm_rev_proxy_key.pem" || copy_default_certs="y"
   if [ $copy_default_certs = "y" ]; then {
        echo "copying default certs to $static_data_path/certs/"
        ssh $remote_server_addr "mkdir -p $static_data_path/certs"
	rsync -azvP  misc/default_certs/* $remote_server_addr:$static_data_path/certs/.
   }
   fi
}
else {
   ls -l static/certs/fm_rev_proxy_cert.pem || copy_default_certs="y"
   ls -l static/certs/fm_rev_proxy_key.pem || copy_default_certs="y"
   if [ $copy_default_certs = "y" ]; then {
   	echo "copying default certs to static/certs dir"
	mkdir -p static/certs
	cp misc/default_certs/* static/certs/.
   }
   fi
   echo $IS_DIRTY
   if [ "$IS_DIRTY" = "dirty" ]; then
   {
     echo "Code is dirty, cannot upload to master fm, exiting"
   }
   else {
      upload_to_sanjaya_interactive
      tar_images
   }
   fi
}
fi

echo "FM Version: $FM_VERSION"
echo "Created images with the tag $FM_VERSION"


