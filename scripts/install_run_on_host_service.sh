set -e
echo "You would need sudo access to run this script"

FM_STATIC_DIR=$(pwd)

echo Working Directory: $FM_STATIC_DIR

rm run_on_host_fifo || true
rm run_on_host_updater_fifo || true

mkfifo run_on_host_fifo || true
mkfifo run_on_host_updater_fifo || true

sudo chmod ugo+rwx run_on_host.sh
sudo chmod ugo+rwx run_on_host_updater.sh

# create run_on_host service
echo -e "[Unit]\nDescription=Run on host service - This will be used to run commands outside docker-context"> run_on_host.service
echo -e "\n[Service]\nType=simple\nUser=root\nExecStart=/bin/bash -c 'exec ./run_on_host.sh'" >> run_on_host.service
echo -e "Restart=always" >> run_on_host.service
echo -e "WorkingDirectory=$FM_STATIC_DIR" >> run_on_host.service
echo -e "\n[Install]\nWantedBy=multi-user.target" >> run_on_host.service


# start, enable run_on_host service
sudo cp run_on_host.service /etc/systemd/system/.
rm run_on_host.service
sudo systemctl daemon-reload
sudo systemctl start run_on_host.service
sudo systemctl enable run_on_host.service
echo "created a sytemctl service named run_on_host.service"


# create run_on_host service
echo -e "[Unit]\nDescription=Updates run on host service"> run_on_host_updater.service
echo -e "\n[Service]\nType=simple\nUser=root\nExecStart=/bin/bash -c 'exec ./run_on_host_updater.sh'" >> run_on_host_updater.service
echo -e "Restart=always" >> run_on_host_updater.service
echo -e "WorkingDirectory=$FM_STATIC_DIR" >> run_on_host_updater.service
echo -e "\n[Install]\nWantedBy=multi-user.target" >> run_on_host_updater.service

# start, enable run_on_host_updater service
sudo cp run_on_host_updater.service /etc/systemd/system/.
rm run_on_host_updater.service
sudo systemctl daemon-reload
sudo systemctl start run_on_host_updater.service
sudo systemctl enable run_on_host_updater.service
echo "created a sytemctl service named run_on_host_updater.service"

sudo systemctl status run_on_host.service
sudo systemctl status run_on_host_updater.service


