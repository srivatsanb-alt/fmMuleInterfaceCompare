#! /bin/bash
set -e

remote_fm_server=$1
client_name=$2
home_path=$3

nginx -v || apt-get install nginx -y
conf_shasum=$(shasum mfm_rev_tunnel_nginx.conf | awk '{print $1}')
echo $conf_shasum
current_conf_shasum=$(shasum /etc/nginx/nginx.conf | awk '{print $1}')
echo $current_conf_shasum

if [ "$current_conf_shasum" = "$conf_shasum" ]; then {
  echo "Nginx running with the right config"
}
else {
  echo "Will update nginx conf"
  cp mfm_rev_tunnel_nginx.conf /etc/nginx/nginx.conf
  echo "Updated nginx conf"
  nginx -t
  systemctl restart nginx.service 
}
fi

# create rev_tunnel.service file
ssh_key_path=$home_path"/.ssh/id_ed25519"
if [ -f "$ssh_key_path" ]; then
    echo "$ssh_key_path exists."
else {
  echo "ssh key: $ssh_key_path doesn't exists"
  exit
}
fi

echo -e "[Unit]\nDescription=Keep reverse tunnel for client $client_name always open\nAfter=network.target" > rev_tunnel_$client_name.service
echo -e "\n[Service]\nEnvironment='AUTOSSH_GATETIME=0'\nExecStart=autossh -M 0 -o 'ServerAliveInterval 30' -o 'ServerAliveCountMax 3' -N -R 9010:localhost:9010 $remote_fm_server" -i $ssh_key_path >> rev_tunnel_$client_name.service
echo -e "Restart=always" >> rev_tunnel_$client_name.service
echo -e "\n[Install]\nWantedBy=multi-user.target" >> rev_tunnel_$client_name.service

# enable service 
cp rev_tunnel_$client_name.service /etc/systemd/system/.
rm rev_tunnel_$client_name.service
systemctl daemon-reload 
systemctl start rev_tunnel_$client_name.service
systemctl enable rev_tunnel_$client_name.service

sleep 5
systemctl status nginx.service 
systemctl status rev_tunnel_$client_name.service
