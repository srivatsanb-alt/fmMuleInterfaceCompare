#! /bin/bash

source docker_env.sh

LOGS=$FM_LOG_DIR
TS=$(date +'%H%M%S')

start() {
    echo "starting fleet manager"
    poetry run python main.py > /app/logs/fm.out 2>&1 &
    echo "starting uvicorn"
    poetry run uvicorn app.main:app --host 0.0.0.0 --port $FM_PORT > /app/logs/uvicorn.out 2>&1 &
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
   #poetry run python -m app.mule.ati.orchestrator.orchestrator.regenerate_config $ATI_CONFIG	
}

save_fleet_log
redis-cli -u $FM_REDIS_URI flushall
start
tail -f /dev/null



