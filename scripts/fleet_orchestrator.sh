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
    poetry run python /app/app/main.py 2>&1 &

    echo "starting plugins uvicorn, listening on port $PLUGIN_PORT"
    poetry run python /app/plugins/plugin_app.py 2>&1 &

    echo "starting plugins worker"
    poetry run python plugins/plugin_rq.py 2>&1 &
}

fm_init() {
   cd /app
   poetry run python scripts/set_token.py
   poetry run python fm_init.py
}

run_simulator() {
  poetry run python debug.py establish_all_sherpa_ws > $LOGS/simulator.log 2>&1 &
  poetry run python debug.py simulate > $LOGS/simulator.log 2>&1 &
}


redis-server --port $REDIS_PORT > $LOGS/redis.log 2>&1 &
sleep 2
fm_init
start

#simulator will be started only if simulate is set to true in fleet_config
run_simulator

#to keep the docker alive - run a never ending process
cd /app
poetry run python scripts/restart.py 2>&1
