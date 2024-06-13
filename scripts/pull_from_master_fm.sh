set -e
source scripts/docker_utils.sh

set_timezone_dc()
{
    CONTINENT=$(echo $TZ | awk -F '/' '{ print $1 }')
    CITY=$(echo $TZ | awk -F '/' '{ print $2 }')
    sed -i "s/Asia/$CONTINENT/g" $FM_STATIC_DIR/docker_compose_v$FM_VERSION.yml
    sed -i "s/Kolkata/$CITY/g" $FM_STATIC_DIR/docker_compose_v$FM_VERSION.yml
}

download_pull_fm_update()
{
  redis-cli -h $REDIS_HOST -p $REDIS_PORT set update_done false

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

   download_dc_yml=$(curl -o $FM_STATIC_DIR/docker_compose_v$FM_VERSION.yml -w "%{http_code}" $HTTP_SCHEME://$STATIC_FILE_AUTH_USERNAME:$STATIC_FILE_AUTH_PASSWORD@$MASTER_FM_IP:$MASTER_FM_PORT/api/static/downloads/fm/$FM_VERSION/docker_compose_v$FM_VERSION.yml)

   if [ $download_dc_yml != 200 ]; then
   {
      echo "Unable to download docker-compose yml file corresponding to $FM_VERSION"
      exit 1
   }
   fi

   set_timezone_dc

   docker-compose -f $FM_STATIC_DIR/docker_compose_v$FM_VERSION.yml config | grep image | awk -v registry="$MASTER_FM_IP:$MASTER_FM_PORT/" '{print registry$2}' | xargs -I % echo "will download %"
   docker-compose -f $FM_STATIC_DIR/docker_compose_v$FM_VERSION.yml config | grep image | awk -v registry="$MASTER_FM_IP:$MASTER_FM_PORT/" '{print registry$2}' | xargs -I % docker pull %
   docker-compose -f $FM_STATIC_DIR/docker_compose_v$FM_VERSION.yml config | grep image | awk '{print $2}' | xargs -I % docker tag "$MASTER_FM_IP:$MASTER_FM_PORT/"% %
   docker logout $MASTER_FM_IP:$MASTER_FM_PORT

   all_reqd_images_available=$(are_all_dc_images_available $FM_VERSION)
   if [ "$all_reqd_images_available" != "yes" ]; then
   {
      echo "$all_reqd_images_available....exiting"
      redis-cli -h $REDIS_HOST -p $REDIS_PORT set update_done false
      echo -e "Unable to complete the update to $FM_VERSION"
      exit 1
   }
   fi

   redis-cli -h $REDIS_HOST -p $REDIS_PORT set update_done true
   echo "Update Done!"
}
