{
  volume_id=$(docker inspect fleet_db | awk '/volumes/ {split($2, array, "/"); i=1; while (i!=-1) { if (array[i] == "volumes") {print array[i+1]; break;} else i=i+1}}')
  echo "will stop fleet_db, delete docker volume $volume_id"
  docker stop fleet_db
  docker rm fleet_db
  docker volume rm $volume_id
}  ||  {
    echo "couldn't clear cb on fm server"
}
