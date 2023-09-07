set -e 
source /app/scripts/pull_from_master_fm.sh

MASTER_FM_IP=$1
MASTER_FM_PORT=$2
HTTP_SCHEME=$3
FM_VERSION=$4
MASTER_FM_REGISTRY_USERNAME=$5
MASTER_FM_REGISTRY_PASSWORD=$6
STATIC_FILE_AUTH_USERNAME=$7
STATIC_FILE_AUTH_USERNAME=$8

download_pull_fm_update $MASTER_FM_IP $MASTER_FM_PORT $HTTP_SCHEME $FM_VERSION $resgitry_username $registry_password $static_file_auth_username $static_file_auth_password

