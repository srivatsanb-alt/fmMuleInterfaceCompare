#! /bin/bash

source env.sh

LOGS=$FM_LOG_DIR
TS=$(date +'%H%M%S')

shutdown() {
    echo "shutting down fleet manager"
    poetry run python scripts/shutdown.py
    echo "shutting down uvicorn"
    ps -f | grep uvicorn | awk '{print $2}' | xargs kill -9 >& /dev/null
}

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

shutdown
save_fleet_log
redis-cli flushall
start
