#! /bin/bash
set -e

LOGS=$FM_LOG_DIR
TS=$(date +'%H%M%S')

start() {
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

set_max_connections() {
  poetry run python -c "from scripts.psql_connection_settings import create_psql_db_config; create_psql_db_config();"

  MC=$(poetry run python -c "from scripts.psql_connection_settings import get_max_psql_connections_from_mongo; get_max_psql_connections_from_mongo();")

  # set env var
  export PSQL_MAX_CONNECTIONS=$MC

  echo "Setting PSQL_MAX_CONNECTIONS to $MC"

  #modify psql conf
  n=$(cat /app/static/psql/psql_backup/postgresql.conf | grep "max_connections = $MC" | wc -l)
  if [ "$n" -eq "1" ] ; then
     echo "Already modified psql max connections to $MC"
  else
     sed -i "s/max_connections/#max_connections/g" /app/static/psql/psql_backup/postgresql.conf
     echo "max_connections = $MC" >> /app/static/psql/psql_backup/postgresql.conf
     echo "Will set psql max connections to $MC"
     docker restart fleet_db
     echo "Restarted fleet_db container"
  fi
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

  FILE_PIPE="/app/static/run_on_host_updater_fifo"
  if [ -p $FILE_PIPE ]; then
    echo "update" > $FM_STATIC_DIR/run_on_host_updater_fifo
    echo "Sent update message to run_on_host_update_fifo"
  fi

}

set_max_connections
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
