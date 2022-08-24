#!/bin/bash
set -e

export DOCKER_HOST=ssh://ati@$1

echo "Pushing to $1"

IMAGE_ID=$(docker images --format '{{.ID}} {{.Repository}} {{.Tag}}' fleet_manager)
BRANCH=$(git rev-parse --abbrev-ref HEAD)
GIT_TAG="$(git rev-parse HEAD) $(git diff --quiet || echo 'dirty')" 
IMAGE_ID="$IMAGE_ID built on $USER@$(hostname) from $GIT_TAG branch $BRANCH $(date)"

echo "IMAGE_ID: $IMAGE_ID"

echo "Building fleet manager docker image"

# docker image build -t fleet_manager -f Dockerfile .
# docker image build --build-arg image_meta="${IMAGE_ID}" -t fleet_manager:$GIT_TAG -f Dockerfile .

# Stop the container if it's already running
echo "Stopping and removing old fleet manager docker image"
docker stop fleet_manager 
docker rm fleet_manager

echo "Running docker image on the server $1"
docker run -d \
       --name fm_container \
       -v /tmp:/tmp \
       -v /app/logs:~/logs \
       -v /app/static:~/static \
        fleet_manager

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


