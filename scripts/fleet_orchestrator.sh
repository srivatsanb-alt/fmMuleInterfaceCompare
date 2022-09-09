#! /bin/bash
LOGS=$FM_LOG_DIR
TS=$(date +'%H%M%S')

start() {
    echo "starting fleet manager"
    poetry run python /app/main.py > $LOGS/fm.out 2>&1 &
    echo "starting uvicorn"
    poetry run uvicorn app.main:app --host 0.0.0.0 --port $FM_PORT > $LOGS/uvicorn.out 2>&1 &
}


save_fleet_log() {
    echo "saving old fleet manager logs"
    mkdir -p $LOGS/backup
    for f in $(ls $LOGS); do
      [[ "$f" == "backup" ]] && continue
      mv $LOGS/$f $LOGS/backup/$f.$TS 2>/dev/null
    done
}


regenerate_mule_config() {
   echo "regeneraing mule config"  
   #poetry run python regenerate_config.py
}


set_postgres_uri() {
   echo "finding postgres uri"
   network_ip=docker inspect --format '{{ .NetworkSettings.IPAddress }}' fleet_manager_1	
   export FM_DATABASE_URI="postgresql://$PGUSER:$PGPASSWORD@$network_ip:$PGPORT"
}

set_postgres_uri
regenerate_mule_config
save_fleet_log
redis-server > $LOGS/redis.log 2>&1 &
redis-cli flushall

start
tail -f /dev/null



