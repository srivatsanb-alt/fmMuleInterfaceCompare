#! /bin/bash

source env.sh

LOGS=$FM_LOG_DIR
TS=$(date +'%H%M%S')

start() {
    echo "starting fleet manager"
    poetry run python main.py > $LOGS/fm.out 2>&1 &
    echo "starting uvicorn"
    poetry run uvicorn app.main:app --host 0.0.0.0 > $LOGS/uvicorn.out 2>&1 &
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
   poetry run python -m app.mule.ati.orchestrator.orchestrator.regenerate_config $ATI_CONFIG	
}

regenerate_mule_config
save_fleet_log
start



