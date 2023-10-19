while true
do
    echo "run on host service is active!"
    read service_type < run_on_host_fifo
        echo "new service request: $service_type"
        if [ $service_type = "restart_all_services" ]; then
	    FM_VERSION=$(cat restart.with)
	    docker-compose -p fm -f docker_compose_v$FM_VERSION.yml down || echo "Unable to stop FM"
            docker-compose -p fm -f docker_compose_v$FM_VERSION.yml up -d || echo "Unable to bring up FM with $FM_VERSION"
            echo "Restarted FM"
        else
            echo "unknown service_type <$service_type>"
        fi
done
