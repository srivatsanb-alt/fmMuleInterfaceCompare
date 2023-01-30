echo "loading postgres image"
docker image load -i postgres_14_0.tar
echo "loaded postgres image"
echo "loading registry v2 image"
docker image load -i registry_v2.tar
echo "loaded registry_v2 image"
echo "loading fm nginx image"
docker image load -i fm_nginx.tar
echo "loaded fm nginx image"
echo "loading fm_base image"
docker image load -i fm_base.tar
echo "loaded fm_base image"
echo "loading fm_final image"
{
   docker image load -i fm_final.tar
   echo "loaded fm final image successfully"
} || echo "Unable to fm final image"

