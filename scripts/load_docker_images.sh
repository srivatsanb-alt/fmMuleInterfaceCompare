echo "loading nginx image"
docker image load -i nginx_1_14_0.tar
echo "loaded nginx image"
echo "loading postgres image"
docker image load -i postgres_14_0.tar
echo "loaded postgres image"
echo "loading fm_base image"
docker image load -i fm_base.tar
echo "loaded fm_base image"
