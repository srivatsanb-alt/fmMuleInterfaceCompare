#!/bin/bash
set -e

export DOCKER_HOST=ssh://ati@$1
source env.sh

echo "Pushing to $1"

IMAGE_ID=$(docker images --format '{{.ID}} {{.Repository}} {{.Tag}}' fleet_manager)
BRANCH=$(git rev-parse --abbrev-ref HEAD)
GIT_TAG="$(git rev-parse HEAD) $(git diff --quiet || echo 'dirty')" 
IMAGE_ID="$IMAGE_ID built on $USER@$(hostname) from $GIT_TAG branch $BRANCH $(date)"

docker image build --build-arg image_meta="${IMAGE_ID}" -t fleet_manager -f Dockerfile.arm64 .

#echo "Starting postgres"
#docker stop postgres
#docker rm postgres 
#docker run -d \
#        -e POSTGRES_USER=$postgres_user \
#        -e POSTGRES_PASSWORD=$postgres_pwd \
#        -p $postgres_port:$postgres_port \
#        postgres:latest

#docker stop redis 
#docker rm redis
#echo "Starting redis"
#docker run -d \
#        --name redis \
#        -p $redis_port:$redis_port \
#         redis/redis-stack:latest 

# Stop the container if it's already running
docker stop fleet_manager 
docker rm fleet_manager

echo "building fleet manager docker image"
docker build \
	-t fleet_manager:$fm_branch \
	-f ./Dockerfile .	

for info in $IMAGE_ID
do
  PREV_IMAGE_ID=$info
  docker rmi $PREV_IMAGE_ID
  echo "deleting previous fleet_manager:latest docker build, id: $PREV_IMAGE_ID"
  break
done

