while true
do
    echo "run on host updater service is active!"
    read service_type < run_on_host_updater_fifo
        echo "new service request: $service_type"
        if [ $service_type = "update" ]; then
	    chmod ugo+rwx run_on_host.sh
	    systemctl daemon-reload
	    systemctl restart run_on_host.service
        else
            echo "unknown service_type <$service_type>"
        fi
done
