#!/bin/bash

branch_name=$(git rev-parse --abbrev-ref HEAD)

./scripts/setup_fm.sh
docker compose  -p fm -f static/docker_compose_v$branch_name.yml down
docker compose  -p fm -f static/docker_compose_v$branch_name.yml up -d
