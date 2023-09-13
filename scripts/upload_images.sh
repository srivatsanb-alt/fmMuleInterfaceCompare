set -e

upload_to_sanjaya() 
{
   read -p "Should push images to Sanjaya? (y/n) - " push_to_sanjaya
   if [ "$push_to_sanjaya" = "y" ]; then
   {
      MASTER_FM_IP="sanjaya.atimotors.com"
      MASTER_FM_PORT="443"
      HTTP_SCHEME="https"
      read -p "Sanjaya Username: " master_fm_username
      read -p "Sanjaya Password: " master_fm_password
      resp=$(curl -X "POST" -H "Content-Type: application/json" -d '{"name": "'$master_fm_username'", "password": "'$master_fm_password'"}' https://sanjaya.atimotors.com/api/v1/master_fm/user/login)
      access_token=$(echo $resp | jq .access_token | sed -e 's/^"//' -e 's/"$//')
      registry_username=$(echo $resp | jq .static_files_auth.username | sed -e 's/^"//' -e 's/"$//')
      registry_password=$(echo $resp | jq .static_files_auth.password | sed -e 's/^"//' -e 's/"$//')
      echo "Access token: $access_token"
      echo "Registry username: $registry_username"
      echo "Registry password: $registry_password"
      echo "Software was last updated at: $LAST_COMMIT_DT" > static/release.dt
      echo "Images were created at: $(date)" > static/release.dt
      curl -H "X-User-Token: $access_token" -d @static/release.dt $HTTP_SCHEME://$MASTER_FM_IP:$MASTER_FM_PORT/upload/fm/$FM_VERSION
      curl -H "X-User-Token: $access_token" -d @static/docker_compose_$FM_VERSION.yml $HTTP_SCHEME://$MASTER_FM_IP:$MASTER_FM_PORT/upload/fm/$FM_VERSION 
      rm static/release.dt
      docker login --username $registry_username --password $registry_password $MASTER_FM_IP:$MASTER_FM_PORT
      docker-compose -f static/docker_compose_v$FM_VERSION.yml config | grep image | awk '{print $2}' | xargs -I % docker tag % "$MASTER_FM_IP:$MASTER_FM_PORT/"%
      docker-compose -f static/docker_compose_v$FM_VERSION.yml config | grep image | awk -v repository="$MASTER_FM_IP:$MASTER_FM_PORT/" '{print repository$2}' | xargs -I % docker push %
      docker logout $MASTER_FM_IP:$MASTER_FM_PORT
   }
   fi
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



