set -e
# base images
echo "loading postgres image"
docker image load -i postgres_14_0.tar
echo "loaded postgres image"
echo "loading registry v2 image"
docker image load -i registry_v2.tar
echo "loaded registry_v2 image"
echo "loading nginx:1.23.3 image"
docker image load -i nginx_1_23_3.tar
echo "loaded nginx:1.23.3 image"
echo "loading fm_base image"
docker image load -i fm_base.tar
echo "loaded fm_base image"

echo "loading grafana_9_5_2 image"
docker image load -i grafana_9_5_2.tar
echo "loaded grafana_9_5_2 image"


# not required while pushing from fleet_manager repo
echo "loading fm nginx image"
docker image load -i fm_nginx.tar || echo "unable to load nginx final image"


echo "loading fm_final image"
docker image load -i fm_final.tar || echo "unable to load fm final image successfully"
