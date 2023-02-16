echo "Building docker images for configure_fm app"
docker image build -f docker_files/Dockerfile.base -t configure_fm:base .
docker image build -f docker_files/Dockerfile -t configure_fm:dev .
