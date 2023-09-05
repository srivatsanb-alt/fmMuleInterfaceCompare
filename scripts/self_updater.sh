set -e 
MASTER_FM_IP=$1
MASTER_FM_PORT=$2
HTTP_SCHEME=$3
FM_VERSION=$4 
MASTER_FM_REGISTRY_USERNAME=$6 
MASTER_FM_REGISTRY_PASSWORD=$7
STATIC_FILE_AUTH_USERNAME=$8
STATIC_FILE_AUTH_USERNAME=$9

echo -e "will try to download, pull from $MASTER_FM_IP:$MASTER_FM_PORT"
docker login -u $MASTER_FM_REGISTRY_USER_NAME -p $MASTER_FM_REGISTRY_PASSWORD $MASTER_FM_IP/$MASTER_FM_PORT
curl -X "GET" $HTTP_SCHEME://$MASTER_FM_IP:$MASTER_FM_PORT/downloads/fm/$FM_VERSION/docker_compose_$FM_VERSION.yml
docker-compose -f docker_compose_v$FM_VERSION.yml config | grep image | awk -v repository="$MASTER_FM_IP:$MASTER_FM_PORT/" '{print repository$2}' | xargs -I % docker pull %
docker-compose -f docker_compose_v$FM_VERSION.yml config | grep image | awk '{print $2}' | xargs -I % docker tag "$MASTER_FM_IP:$MASTER_FM_PORT/"% % 
docker logout


