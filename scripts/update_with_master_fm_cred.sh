set -e
source /app/scripts/pull_from_master_fm.sh

MASTER_FM_IP="sanjaya.atimotors.com"
MASTER_FM_PORT="443"
HTTP_SCHEME="https"

read -p "Sanjaya Username: " master_fm_username
read -p "Sanjaya Password: " master_fm_password
read -p "FM version: " FM_VERSION
read -p "Is this build in production? (y/n) " prod_release

resp=$(curl -X "POST" -H "Content-Type: application/json" -d '{"name": "'$master_fm_username'", "password": "'$master_fm_password'"}' https://sanjaya.atimotors.com/api/v1/master_fm/user/login)

access_token=$(echo $resp | jq .access_token | sed -e 's/^"//' -e 's/"$//')
registry_username=$(echo $resp | jq .registry_auth.username | sed -e 's/^"//' -e 's/"$//')
registry_password=$(echo $resp | jq .registry_auth.password | sed -e 's/^"//' -e 's/"$//')
static_file_auth_username=$(echo $resp | jq .static_files_auth.username | sed -e 's/^"//' -e 's/"$//')
static_file_auth_password=$(echo $resp | jq .static_files_auth.password | sed -e 's/^"//' -e 's/"$//')

echo "Got all the credentials to update"

download_pull_fm_update $MASTER_FM_IP $MASTER_FM_PORT $HTTP_SCHEME $FM_VERSION $registry_username $registry_password $static_file_auth_username $static_file_auth_password

