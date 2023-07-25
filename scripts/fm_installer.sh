set -e

setup_mode=$(zenity --list --column "Setup Mode" dev production)
DIRECT_ACCESS="Have direct access to sanjaya.atimotors.com"
VPN_REV_TUNNEL_ACCESS="Will access sanjaya.atimotors.com through VPN reverse tunnel"

if [ $setup_mode = "dev" ] ; then {
   FM_VERSION="fm_dev"
   MASTER_FM_ACCESS_TYPE="$DIRECT_ACCESS"
   REGISTRY_USERNAME="ati_dev"
   TZ="Asia/Kolkata" 
   user_inputs=$(zenity --forms --title="Install/update FM" \
    --text "Fill in FM installation details" \
    --add-password="Docker registry password" \
   )  
   echo $UPDATE_STATIC_FILES
   REGISTRY_PASSWORD=$(echo $user_inputs | awk -F "|" '{print $2}')
}
else {
  user_inputs=$(zenity --forms --title="Install/update FM" \
    --text "Fill in FM installation details" \
    --add-entry="FM version to be installed" \
    --add-entry="Previous FM version" \
    --add-entry="TimeZone" \
    --add-entry="Docker registry username" \
    --add-password="Docker registry password" \
    --add-password="User: $USER, Password (sudo access): "
   )
   FM_VERSION=$(echo $user_inputs | awk -F "|" '{print $1}')
   PREV_FM_VERSION=$(echo $user_inputs | awk -F "|" '{print $2}')
   TZ=$(echo $user_inputs | awk -F "|" '{print $3}')
   REGISTRY_USERNAME=$(echo $user_inputs | awk -F "|" '{print $4}')
   REGISTRY_PASSWORD=$(echo $user_inputs | awk -F "|" '{print $5}')
   HOST_PASSWORD=$(echo $user_inputs | awk -F "|" '{print $6}')	
   MASTER_FM_ACCESS_TYPE=$(zenity \
     --width 600 \
     --height 400 \
     --list \
     --title "Access to master FM" \
     --column "Access" \
     "$VPN_REV_TUNNEL_ACCESS" \
     "$DIRECT_ACCESS"
   )
}
fi


echo Master fm access type $MASTER_FM_ACCESS_TYPE
pull_server="sanjaya.atimotors.com"
pull_port="443"
run_docker_as_host=0
http_scheme="https"
if [ "$MASTER_FM_ACCESS_TYPE" = "$VPN_REV_TUNNEL_ACCESS" ] ; then { 
   pull_server="localhost"
   pull_port="9010"
   http_scheme="http"
   if [ $(uname) != "Linux" ] ; then {
      zenity --error --text "Can run docker as host only in Linux systems, Exiting" --width 400 --height 100
      exit
   }
   fi
   run_docker_as_host=1
}
fi


check_if_pull_error() {
   e=$1
   if [ "$e" != " " ] ; then {
       zenity --error --text "$e" --width 400 --height 100
       exit
  }
  fi
}

pull_fm_images() {
    echo "Will pull FM images from $pull_server, $pull_port"
    docker login -u $REGISTRY_USERNAME -p $REGISTRY_PASSWORD $pull_server:$pull_port
    
    pull_error=" "
    docker pull $pull_server:$pull_port/grafana/grafana:9.5.2 || pull_error="Unable to fetch grafana image"
    docker pull $pull_server:$pull_port/fleet_manager:$FM_VERSION || pull_error="Unable to fetch fleet manager image"
    if [ $run_docker_as_host = 1 ]; then {
       docker pull $pull_server:$pull_port/fm_nginx_host:1.23.3 || pull_error="Unable to fetch fm_nginx_host image"
    }
    else {
       docker pull $pull_server:$pull_port/fm_nginx_bridge:1.23.3 || pull_error="Unable to fetch fm_nginx_bridge image"	    
    }
    fi
    docker pull $pull_server:$pull_port/postgres:14.0 || pull_error="Unable to fetch postgres image"              
    docker pull $pull_server:$pull_port/grafana/grafana:9.5.2 || pull_error="Unable to fetch grafana image"              
    docker pull $pull_server:$pull_port/registry:2 || pull_error="Unable to fetch registry image"

    check_if_pull_error "$pull_error"

}
#pull_fm_images


download_static_files() {
   curl $http_scheme://$pull_server:$pull_port/downloads/fm_v$FM_VERSION/static_files.tar  --cacert /etc/ssl/certs/ca-certificates.crt
   tar -xvf static_files.tar
}

if zenity --question --text "Update static files" --width 200 --height 100 ; then {
  download_static_files
}
else {
  echo "Not downloading the static files"
}
fi


maybe_change_tz() {
  echo "will set timezone to $TZ"
  if [ $TZ != "Asia/Kolkata" ]; then { 
     TZ_1=$(echo $TZ | awk -F "/" '{print $1}')
     TZ_2=$(echo $TZ | awk -F "/" '{print $2}')
     sed -i "s/Asia/$TZ_1/g" static_v$FM_VERSION/docker_compose_host.yml
     sed -i "s/Asia/$TZ_1/g" static_v$FM_VERSION/docker_compose_bridge.yml
     sed -i "s/Asia/$TZ_2/g" static_v$FM_VERSION/docker_compose_host.yml
     sed -i "s/Kolkata/$TZ_2/g" static_v$FM_VERSION/docker_compose_bridge.yml
  }
  fi
}
maybe_change_tz
