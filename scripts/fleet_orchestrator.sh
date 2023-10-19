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



update_run_on_host_service() {

  FILE="/app/static/run_on_host_updater.sh"
  if [ -f $FILE ]; then
    echo "File $FILE exists."
  else
    echo "Copying $FILE to static dir"
    cp /app/misc/run_on_host/run_on_host_updater.sh /app/static/.
  fi

  FILE="/app/static/install_run_on_host_service.sh"
  if [ -f $FILE ]; then
    echo "File $FILE exists."
  else
    echo "Copying $FILE to static dir"
    cp /app/scripts/install_run_on_host_service.sh /app/static/.
  fi

  cp misc/run_on_host/run_on_host.sh /app/static/.
  
  FILE="/app/static/run_on_host_updater_fifo"
  if [ -f $FILE ]; then 
    echo "update" > /app/static/run_on_host_updater_fifo
  fi

}


redis-server --port $REDIS_PORT > $LOGS/redis.log 2>&1 &
sleep 2
fm_init
start

#simulator will be started only if simulate is set to true in fleet_config
run_simulator

#to keep the docker alive - run a never ending process
cd /app

update_run_on_host_service

poetry run python scripts/restart.py 2>&1
