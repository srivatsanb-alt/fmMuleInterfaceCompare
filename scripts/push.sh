#!/bin/bash
set -e
export DOCKER_HOST=ssh://ati@$1
echo "Pushing to $1"

IMAGE_ID=$(docker images --format '{{.ID}} {{.Repository}} {{.Tag}}' fleet_manager)
BRANCH=$(git rev-parse --abbrev-ref HEAD)
GIT_TAG="$(git rev-parse HEAD) $(git diff --quiet || echo 'dirty')"
IMAGE_ID="$IMAGE_ID built on $USER@$(hostname)_from $GIT_TAG branch $BRANCH_$(date)"

echo "IMAGE_ID: $IMAGE_ID"

echo "Building fleet manager docker image"
#docker image build --build-arg IMAGE_ID="${IMAGE_ID}" -t fleet_manager_base -f Dockerfile.base .
docker image build --build-arg IMAGE_ID="${IMAGE_ID}" -t fleet_manager -f Dockerfile .

echo "Running docker image on the server $1"
docker-compose -p fleet up 


