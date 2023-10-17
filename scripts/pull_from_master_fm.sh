set -e

set_timezone()
{
    CONTINENT=$(echo $TZ | awk -F '/' '{ print $1 }')
    CITY=$(echo $TZ | awk -F '/' '{ print $2 }')
    sed -i "s/Asia/$CONTINENT/g" static/docker_compose_v$FM_VERSION.yml
    sed -i "s/Asia/$CITY/g" static/docker_compose_v$FM_VERSION.yml
}

download_pull_fm_update()
{
  redis-cli -p $REDIS_PORT set update_done false

   MASTER_FM_IP=$1
   MASTER_FM_PORT=$2
   HTTP_SCHEME=$3
   FM_VERSION=$4
   MASTER_FM_REGISTRY_USERNAME=$5
   MASTER_FM_REGISTRY_PASSWORD=$6
   STATIC_FILE_AUTH_USERNAME=$7
   STATIC_FILE_AUTH_PASSWORD=$8
   echo -e "will try to download, pull fm: $FM_VERSION from $HTTP_SCHEME://$MASTER_FM_IP:$MASTER_FM_PORT"
   docker login --username $MASTER_FM_REGISTRY_USERNAME --password $MASTER_FM_REGISTRY_PASSWORD  $MASTER_FM_IP:$MASTER_FM_PORT
   download_dc_yml=$(curl -o /app/static/docker_compose_v$FM_VERSION.yml -w "%{http_code}" $HTTP_SCHEME://$STATIC_FILE_AUTH_USERNAME:$STATIC_FILE_AUTH_PASSWORD@$MASTER_FM_IP:$MASTER_FM_PORT/api/static/downloads/fm/$FM_VERSION/docker_compose_v$FM_VERSION.yml)
   if [ $download_dc_yml != 200 ]; then
   {
      echo "Unable to download docker-compose yml file corresponding to $FM_VERSION"
      exit 1
   }
   fi
   set_timezone
   #cp /app/static/docker_compose_v$FM_VERSION.yml /app/static/docker_compose_latest.yml
   docker-compose -f /app/static/docker_compose_v$FM_VERSION.yml config | grep image | awk -v registry="$MASTER_FM_IP:$MASTER_FM_PORT/" '{print registry$2}' | xargs -I % echo "will download %"
   docker-compose -f /app/static/docker_compose_v$FM_VERSION.yml config | grep image | awk -v registry="$MASTER_FM_IP:$MASTER_FM_PORT/" '{print registry$2}' | xargs -I % docker pull %
   docker-compose -f /app/static/docker_compose_v$FM_VERSION.yml config | grep image | awk '{print $2}' | xargs -I % docker tag "$MASTER_FM_IP:$MASTER_FM_PORT/"% %
   docker logout $MASTER_FM_IP:$MASTER_FM_PORT

   all_reqd_images=$(docker-compose -f /app/static/docker_compose_v$FM_VERSION.yml config | grep image | awk '{print $2}')
   for reqd_image in $all_reqd_images
   do
     if docker image inspect $reqd_image > /dev/null 2>&1 ; then
        echo "$reqd_image pulled successfully."
     else
        echo "$reqd_image pull incomplete..exiting"
        redis-cli -p $REDIS_PORT set update_done false	
	echo -e "Unable to complete the update to $FM_VERSION"
	exit 1
     fi
   done  
   redis-cli -p $REDIS_PORT set update_done true
   echo "Update Done!"

}
