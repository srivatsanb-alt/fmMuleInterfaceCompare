set -e 
source /app/scripts/pull_from_master_fm.sh

MASTER_FM_IP=$1
MASTER_FM_PORT=$2
HTTP_SCHEME=$3
FM_VERSION=$4

# not mapping creds to vars - facing some issues in docker login 
#MASTER_FM_REGISTRY_USERNAME=$5
#MASTER_FM_REGISTRY_PASSWORD=$6
#STATIC_FILE_AUTH_USERNAME=$7
#STATIC_FILE_AUTH_USERNAME=$8

download_pull_fm_update $MASTER_FM_IP $MASTER_FM_PORT $HTTP_SCHEME $FM_VERSION $5 $6 $7 $8

