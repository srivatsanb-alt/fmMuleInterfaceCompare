echo "Building docker images for sanjaya"

docker image build -f docker_files/Dockerfile.base -t sanjaya:base .
docker image build -f docker_files/Dockerfile -t sanjaya:dev .