GIT_TAG=$(git describe --all | awk '{split($0,a,"/"); print a[2];}')

docker-compose  -p $GIT_TAG -f static/docker_compose_v$GIT_TAG.yml down
./scripts/setup_fm.sh
docker-compose  -p $GIT_TAG -f static/docker_compose_v$GIT_TAG.yml up -d