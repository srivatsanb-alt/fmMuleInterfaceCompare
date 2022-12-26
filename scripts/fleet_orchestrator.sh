#! /bin/bash
set -e

LOGS=$FM_LOG_DIR
TS=$(date +'%H%M%S')

start() {

    echo "starting control_module router"
    poetry run python /app/optimal_dispatch/router.py &

    echo "starting fleet manager workers"
    poetry run python /app/main.py > $LOGS/fm.out 2>&1 &

    echo "starting fleet manager uvicorn, listening on port $FM_PORT"
    poetry run uvicorn app.main:app --host 0.0.0.0 --port $FM_PORT > $LOGS/uvicorn.out 2>&1 &

    echo "starting plugins uvicorn, listening on port $PLUGIN_PORT"
    poetry run uvicorn plugins.plugin_app:app --host 0.0.0.0 --port $PLUGIN_PORT > $LOGS/plugin_uvicorn.out 2>&1 &

    echo "starting plugins worker"
    poetry run python plugins/plugin_rq.py > $LOGS/plugin_rq.out 2>&1 &
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
   poetry run python scripts/set_token.py
   poetry run python fm_init.py
}

run_simulator() {
  poetry run python debug.py host_all_mule_app 2>&1 &
  poetry run python debug.py simulate > $LOGS/simulator.log 2>&1 &
}


redis-server --port $REDIS_PORT > $LOGS/redis.log 2>&1 &
sleep 2
fm_init
save_fleet_log
start

#will be run only if simulate is set to true in fleet_config
run_simulator

#to keep the docker alive - run a never ending process
tail -f /dev/null
