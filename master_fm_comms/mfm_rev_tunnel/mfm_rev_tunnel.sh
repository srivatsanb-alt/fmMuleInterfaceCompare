#! /bin/bash
set -e

remote_fm_server=$1
client_name=$2

if [ -z "$remote_fm_server" ]
then
      echo "Invalid arg1 (needs remote server spec. Like username@remote-ip)"
      exit
else
      echo "remote_fm_server set to $remote_fm_server"
fi

if [ -z "$client_name" ]
then
      echo "Invalid arg2 (need client_name, cannot be empty)"
      exit
else
      echo "client_name set to $client_name"
fi


# install autossh if not already present
autossh -V || sudo apt-get install autossh -y


# install nginx if not already present
sudo nginx -v || sudo apt-get install nginx -y


# update nginx.conf
conf_shasum=$(shasum mfm_rev_tunnel_nginx.conf | awk '{print $1}')
echo $conf_shasum
current_conf_shasum=$(shasum /etc/nginx/nginx.conf | awk '{print $1}')
echo $current_conf_shasum
if [ "$current_conf_shasum" = "$conf_shasum" ]; then {
  echo "Nginx running with the right config"
}
else {
  echo "Will update nginx conf"
  sudo cp mfm_rev_tunnel_nginx.conf /etc/nginx/nginx.conf
  echo "Updated nginx conf"
  sudo nginx -t
  sudo systemctl daemon-reload
  sudo systemctl restart nginx.service 
}
fi

# get the ssh key path
ssh_key_file=$(ls -l $HOME/.ssh/. | grep id | grep -v "[pub, rsa]$" | awk '{print $NF}')
ssh_key_path="$HOME/.ssh/$ssh_key_file"
if [ -f "$ssh_key_path" ]; then
    echo "$ssh_key_path exists."
else {
  echo "ssh key: $ssh_key_path doesn't exists"
  exit
}
fi


# create rev_tunnel service
echo -e "[Unit]\nDescription=Keep reverse tunnel for client $client_name always open\nAfter=network.target" > rev_tunnel_$client_name.service
echo -e "\n[Service]\nUser=$USER\nEnvironment='AUTOSSH_GATETIME=0'\nExecStart=autossh -M 0 -o 'ServerAliveInterval 30' -o 'ServerAliveCountMax 3' -N -R 9010:localhost:9010 $remote_fm_server" -i $ssh_key_path >> rev_tunnel_$client_name.service
echo -e "Restart=always" >> rev_tunnel_$client_name.service
echo -e "\n[Install]\nWantedBy=multi-user.target" >> rev_tunnel_$client_name.service

# start, enable rev tunnel service
sudo cp rev_tunnel_$client_name.service /etc/systemd/system/.
rm rev_tunnel_$client_name.service
sudo systemctl daemon-reload 
sudo systemctl start rev_tunnel_$client_name.service
sudo systemctl enable rev_tunnel_$client_name.service
echo "created a sytemctl service named rev_tunnel_$client_name.service"
sleep 5

# print status of nginx, rev_tunnel
sudo systemctl status nginx.service 
sudo systemctl status rev_tunnel_$client_name.service
