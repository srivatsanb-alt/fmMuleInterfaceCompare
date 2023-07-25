set -e

DOCKER_NETWORK=$1
save_nginx_image_alone=$2

# not required while pushing from fleet_manager repo
echo "loading fm nginx image"
if [ "$DOCKER_NETWORK" = "host" ] ; then {
   docker save fm_nginx:1.23.3 > fm_nginx_host.tar
   echo "saved nginx_host image" 
}
elif [ "$DOCKER_NETWORK" = "bridge" ] ; then {
   docker save fm_nginx:1.23.3 >  fm_nginx_bridge.tar
   echo "saved nginx_bridge image"
}
else {
   echo "Need a valid argument - mention docker network (bridge, host)"
   echo "Error!"
   exit
}
fi

if [ $save_nginx_image_alone = "yes" ] ; then {
   exit
}
fi



# base images
docker save postgres:14.0 > postgres_14_0.tar
echo "saved postgres image"
docker save registry:2 > registry_v2.tar
echo "saved registry_v2 image"
docker save nginx:1.23.3 > nginx_1_23_3.tar
echo "saved nginx:1.23.3 image"
docker save fleet_manager_base:dev > fm_base.tar
echo "saved fm_base image"

docker save grafana/grafana:9.5.2 > grafana_9_5_2.tar
echo "saved grafana_9_5_2 image"

docker save fleet_manager:dev > fm_final.tar
echo "saved fm_final image"


