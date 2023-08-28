Help()
{
  # Display Help
  echo "Program to push fleet_manager repo to the FM server!"
  echo
  echo "Args: [-i/W|c|h|v]"
  echo "options:"
  echo "i     Give IP address of the FM server, default is localhost"
  echo "W     Copies the contents of static folder on local machine directly to the FM server, else static files on FM server will be retained"
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

  ssh $usr_name@$ip_address "rsync -aP --exclude={data_backup,psql,mongo,sherpa_uploads} /home/$usr_name/static/. /home/$usr_name/static_old/."
  rsync -azP --no-o --no-g --no-perms --exclude={data_backup,psql,mongo,sherpa_uploads} ./static/* $usr_name@$ip_address:/home/$usr_name/static/.
  rsync -azP ./misc/docker_compose_host.yml $usr_name@$ip_address:/home/$usr_name/static/.

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


get_localhost_ip()
{
     IP=$1
     NETWORK_TYPE=$2
     if [ "$2" == "self" ]; then
        IP=127.0.0.1
     elif ([ "$1" == "localhost" ]) && ([ "$2" != "self" ]); then
         IP=$(ifconfig | grep -C 1 -e $NETWORK_TYPE | awk '/i/ {print $2}')
     fi
     echo $IP
}
