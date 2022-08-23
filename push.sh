source env.sh

#echo "Starting postgres"
#docker stop postgres
#docker rm postgres 
#docker run -d \
#        -e POSTGRES_USER=$postgres_user \
#        -e POSTGRES_PASSWORD=$postgres_pwd \
#        -p $postgres_port:$postgres_port \
#        postgres:latest
#
#
#docker stop redis 
#docker rm redis
#echo "Starting redis"
#docker run -d \
#        --name redis \
#        -p $redis_port:$redis_port \
#         redis/redis-stack:latest 

docker stop fleet_manager 
docker rm fleet_manager

echo "building fleet manager docker image"
docker build \
	-t fleet_manager:$fm_branch \
	-f ./Dockerfile .	

#echo "Starting fleet manager container"
#docker run -d \
#	--name fleet_manager \
#	-v ~/data:/app/data \
#	-v ~/logs:/app/logs \
#	fleet_manager:$fm_branch 



