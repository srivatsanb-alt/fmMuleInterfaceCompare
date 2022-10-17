#! /bin/bash
LOGS=$FM_LOG_DIR
TS=$(date +'%H%M%S')

start() {
    echo "starting fleet manager"
    poetry run python /app/main.py > $LOGS/fm.out 2>&1 &
    echo "starting uvicorn"
    poetry run uvicorn app.main:app --host 0.0.0.0 --port $FM_PORT > $LOGS/uvicorn.out 2>&1 &

    #start control module router
    poetry run python /app/optimal_dispatch/router.py 2>&1 &

}

save_fleet_log() {
    echo "saving old fleet manager logs"
    mkdir -p $LOGS/backup
    for f in $(ls $LOGS); do
      [[ "$f" == "backup" ]] && continue
      mv $LOGS/$f $LOGS/backup/$f.$TS 2>/dev/null
    done
}

fm_init() {
   echo "regeneraing mule config"
   cd /app/mule
   #make build
   cd /app
   poetry run python fm_init.py
}

run_simulator() {
  poetry run python debug.py host_all_mule_app 2>&1 &
  poetry run python debug.py simulate 2>&1 &
}

fm_init
save_fleet_log
redis-server --port $REDIS_PORT > $LOGS/redis.log 2>&1 &
redis-cli flushall
start

#will be run only if simulate is set to true in fleet_config
run_simulator

#to keep the docker alive - run a never ending process
tail -f /dev/null
