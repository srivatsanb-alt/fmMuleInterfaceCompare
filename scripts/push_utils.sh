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
  usr_name=`echo $1 | cut -d@ -f1`
  ip_address=`echo $1 | cut -d@ -f2`
  echo "usr_name $usr_name"
  echo "ip_address $ip_address"
  if ! ssh $1 "[ -d /home/$usr_name/static_old ]"
  then
    echo "Creating directory static_old"
    ssh $usr_name@$ip_address "mkdir /home/$usr_name/static_old"
  else
    echo "Directory static_old already exists"
  fi

  if ! ssh $usr_name@$ip_address "[ -d /home/$usr_name/static ]"
  then
    echo "Creating directory static"
    ssh $usr_name@$ip_address "mkdir /home/$usr_name/static"
  else
    echo "Directory static already exists"
  fi

  ssh $usr_name@$ip_address "rsync -aP /home/$usr_name/static/. /home/$usr_name/static_old/."
  rsync -azP ./static/* $usr_name@$ip_address:/home/$usr_name/static/.
  echo "setting env variable FM_SERVER_IP $FM_SERVER_IP"
  ssh $usr_name@$ip_address "export FM_SERVER_IP=$ip_address"
  echo "Set env variable FM_SERVER_IP "
  ssh $usr_name@$ip_address "echo $FM_SERVER_IP"
  echo "setting env variable DOCKER_REGISTRY_PORT 443"
  ssh $usr_name@$ip_address "export DOCKER_REGISTRY_PORT=443"
  echo "Set env variable DOCKER_REGISTRY_PORT "
  ssh $usr_name@$ip_address "echo $DOCKER_REGISTRY_PORT"
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

create_certs()
{
  CERT_FILE=static/certs/cert.crt	
  KEY_FILE=static/certs/cert.key
  if ([ -f "$CERT_FILE" ]) && ([ -f "$KEY_FILE" ]); then
     echo "FM already has cert files not creating a new one, make sure it was created with the right IP"
  else
     IP=$1
     NETWORK_TYPE=$2
     if [ "$2" == "self" ]; then
	IP=127.0.0.1
     elif ([ "$1" == "localhost" ]) && ([ "$2" != "self" ]); then  
	 IP=$(ifconfig | grep -C 1 -e $NETWORK_TYPE | awk '/i/ {print $2}')
     fi
     echo "will create cert files for FM with ip: $IP $NETWORK_TYPE"
     openssl req -new -newkey rsa:2048 -x509 -sha256 -days 365 -nodes -out cert.crt -keyout cert.key -addext "subjectAltName = IP:$IP"
     mkdir static/certs || true
     mv cert.crt static/certs/
     mv cert.key static/certs/
  fi
}
