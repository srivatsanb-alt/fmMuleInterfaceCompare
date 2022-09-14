#!/bin/bash
set -e
export DOCKER_HOST=ssh://ati@$1
echo "Pushing to $1"

BRANCH=$(git rev-parse --abbrev-ref HEAD)
GIT_TAG="$(git rev-parse HEAD) $(git diff --quiet || echo 'dirty')"
IMAGE_ID="Image built on $USER@$(hostname)_from $GIT_TAG branch $BRANCH_$(date)"
echo "IMAGE_ID: $IMAGE_ID"

echo "Building fleet manager docker image"
docker image build --build-arg IMAGE_ID="${IMAGE_ID}" -t fleet_manager_base -f Dockerfile.base .
docker image build --build-arg IMAGE_ID="${IMAGE_ID}" -t fleet_manager -f Dockerfile .

