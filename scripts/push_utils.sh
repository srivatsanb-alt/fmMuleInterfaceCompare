Help()
{
  # Display Help
  echo "Program to push fleet_manager repo to the FM server!"
  echo
  echo "Args: [-i/W|c|h]"
  echo "options:"
  echo "i     Give IP address of the FM server, default is localhost"
  echo "D     Clears existing db tables - Will reset trips state"
  echo "W     WILL NOT copy the static files from the FM server. Copies the contents of static folder on local machine directly to the FM server."
  echo "c     Checksout the local directory static to its current git commit after the push is successful"
  echo "b     WILL NOT build the base image"
  echo "h     Display help"
}

create_static_backup()
{
  echo $1
  if ! ssh $1 '[ -d static_old ]'
  then
    echo "Creating directory static_old"
    ssh $1 "mkdir /home/ati/static_old"
  else
    echo "Directory static_old already exists"
  fi

  if ! ssh $1 '[ -d static ]'
  then
    echo "Creating directory static"
    ssh $1 "mkdir static"
  else
    echo "Directory static already exists"
  fi

  ssh $1 'rsync -aP /home/ati/static/. /home/ati/static_old/.'
  rsync -azP ./static/* $1:static/.
}

clean_static()
{
  rm -r static
  git checkout static
}

clear_db_on_fm_server()
{
  {
	volume_id=$(docker inspect fleet_db | awk '/volumes/ {split($2, array, "/"); i=1; while (i!=-1) { if (array[i] == "volumes") {print array[i+1]; break;} else i=i+1}}')
  	echo "will stop fleet_db, delete docker volume $volume_id"
  	docker stop fleet_db
  	docker rm fleet_db
  	docker volume rm $volume_id
  }  ||  {
    echo "couldn't clear cb on fm server"
  }
}
