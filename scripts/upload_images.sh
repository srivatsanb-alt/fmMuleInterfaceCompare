set -e

upload_to_sanjaya_interactive() {
   read -p "Should push images to Sanjaya? (y/n) - " push_to_sanjaya
   if [ "$push_to_sanjaya" = "y" ]; then {
      read -p "is this a production release? (y/n) - " prod_release
      read -p "Sanjaya Username: " master_fm_username
      read -p "Sanjaya Password: " master_fm_password
      upload_to_sanjaya $prod_release $master_fm_username $master_fm_password
   }
   fi
}

upload_to_sanjaya() 
{
   prod_release=$1
   master_fm_username=$2
   master_fm_password=$3
   MASTER_FM_IP="staging-sanjaya.atimotors.com"
   if [ "$prod_release" = "y" ]; then
   {
     prod=true
     MASTER_FM_IP="sanjaya.atimotors.com"
   }
   fi
   MASTER_FM_PORT="443"
   HTTP_SCHEME="https"
   resp=$(curl -X "POST" -H "Content-Type: application/json" -d '{"name": "'$master_fm_username'", "password": "'$master_fm_password'"}' $HTTP_SCHEME://$MASTER_FM_IP:$MASTER_FM_PORT/api/v1/master_fm/user/login)
   echo $resp
   access_token=$(echo $resp | jq .access_token | sed -e 's/^"//' -e 's/"$//')
   registry_username=$(echo $resp | jq .registry_auth.username | sed -e 's/^"//' -e 's/"$//')
   registry_password=$(echo $resp | jq .registry_auth.password | sed -e 's/^"//' -e 's/"$//')
   prod=false
   if [ "$prod_release" = "y" ]; then
   {
     prod=true
   }
   fi	      
   echo "Access token: $access_token"
   echo "Registry username: $registry_username"
   echo "Registry password: $registry_password"
   echo "Software was last updated at: $LAST_COMMIT_DT" > static/release.dt
   echo "Images were created at: $(date)" >> static/release.dt 
   upload_dc_file=$(curl -o /dev/null -w "%{http_code}" -H "X-User-Token: $access_token" -F "uploaded_file=@static/docker_compose_v$FM_VERSION.yml" $HTTP_SCHEME://$MASTER_FM_IP:$MASTER_FM_PORT/api/v1/master_fm/fm_client/upload/fm/$FM_VERSION)
   if [ $upload_dc_file != 200 ]; then 
   {
      echo "Unable to upload docker compose file"
      exit 1
   }
   fi
   upload_release_dt=$(curl -o /dev/null -w "%{http_code}" -H "X-User-Token: $access_token" -F "uploaded_file=@static/release.dt" $HTTP_SCHEME://$MASTER_FM_IP:$MASTER_FM_PORT/api/v1/master_fm/fm_client/upload/fm/$FM_VERSION)
   if [ $upload_release_dt != 200 ]; then
   {
      echo "Unable to upload release.dt file"
      exit 1
   }
   fi   
   rm static/release.dt
   docker login --username $registry_username --password $registry_password $MASTER_FM_IP:$MASTER_FM_PORT
   docker-compose -f static/docker_compose_v$FM_VERSION.yml config | grep image | awk '{print $2}' | xargs -I % docker tag % "$MASTER_FM_IP:$MASTER_FM_PORT/"% || exit 1
   docker-compose -f static/docker_compose_v$FM_VERSION.yml config | grep image | awk -v registry="$MASTER_FM_IP:$MASTER_FM_PORT/" '{print registry$2}' | xargs -I % docker push % || exit 1
   docker logout $MASTER_FM_IP:$MASTER_FM_PORT
}

tar_images() {
   read -p "Want to tarball the images? (y/n) - " tar_images
   if [ "$tar_images" = "y" ] ; then
   {
      rm -rf static/fm_setup_v$FM_VERSION || true
      mkdir static/fm_setup_v$FM_VERSION
      touch static/fm_setup_v$FM_VERSION/save_images.sh
      docker-compose -f static/docker_compose_v$FM_VERSION.yml config | grep image | awk '{print $2}' | xargs -I % echo "docker save" % ">" %.tar >> static/fm_setup_v$FM_VERSION/save_images.sh
      cd static/fm_setup_v$FM_VERSION && bash save_images.sh 
      cd ../../
      rm static/fm_setup_v$FM_VERSION/save_images.sh
      touch static/fm_setup_v$FM_VERSION/load_images.sh
      cp static/docker_compose_v$FM_VERSION.yml static/fm_setup_v$FM_VERSION/docker_compose_v$FM_VERSION.yml
      docker-compose -f static/docker_compose_v$FM_VERSION.yml config | grep image | awk '{print $2}' | xargs -I % echo "docker load -i" %.tar >> static/fm_setup_v$FM_VERSION/load_images.sh
      cp readme.pdf static/fm_setup_v$FM_VERSION/readme_v$FM_VERSION.pdf
      cp -r misc/default_certs static/fm_setup_v$FM_VERSION/.
   }
  fi
}



