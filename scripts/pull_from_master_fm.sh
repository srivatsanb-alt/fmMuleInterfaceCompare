set -e

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
   curl -X "GET" $HTTP_SCHEME://$STATIC_FILE_AUTH_USERNAME:$STATIC_FILE_AUTH_PASSWORD@$MASTER_FM_IP:$MASTER_FM_PORT/api/static/downloads/fm/$FM_VERSION/docker_compose_v$FM_VERSION.yml > /app/static/docker_compose_v$FM_VERSION.yml

   docker-compose -f /app/static/docker_compose_v$FM_VERSION.yml config | grep image | awk -v registry="$MASTER_FM_IP:$MASTER_FM_PORT/" '{print registry$2}' | xargs -I % echo "will download %"
   docker-compose -f /app/static/docker_compose_v$FM_VERSION.yml config | grep image | awk -v registry="$MASTER_FM_IP:$MASTER_FM_PORT/" '{print registry$2}' | xargs -I % docker pull %
   docker-compose -f /app/static/docker_compose_v$FM_VERSION.yml config | grep image | awk '{print $2}' | xargs -I % docker tag "$MASTER_FM_IP:$MASTER_FM_PORT/"% %
   docker logout $MASTER_FM_IP:$MASTER_FM_PORT

   redis-cli -p $REDIS_PORT set update_done true
   echo "Update Done!"

}
