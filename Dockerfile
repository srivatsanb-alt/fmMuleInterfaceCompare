From ubuntu:18.04

RUN apt-get update && apt install -y --no-install-recommends \
    curl make net-tools unzip git openssh-client postgresql-client \
    python3.7-dev python3-pip \
    redis && \
    apt-get clean

WORKDIR /app

RUN python3.7 -m pip install -U pip setuptools wheel && \
    python3.7 -m pip install -U poetry==1.1.12

ENV FM_INSTALL_DIR="/app" REDIS_PORT=6379 FM_PORT=8002   
 
ENV FM_REDIS_URI="redis://localhost:$REDIS_PORT" \
    FM_DATABASE_URI="postgresql://$PGUSER:$PGPASSWORD@$PGHOST" \
    FM_MAP_DIR="/static" \
    FM_LOG_DIR="/logs" \
    FM_CONFIG_DIR="/static/config/" \
    MULE_ROOT="$FM_INSTALL_DIR/mule" \
    ATI_CONFIG="/static/mule_config/config.toml" \
    ATI_CONSOLIDATED_CONFIG="/static/mule_config/consolidated.toml"


ARG IMAGE_ID

COPY . /app/
RUN cd /app
RUN mkdir /app/logs
RUN mkdir /static
RUN mkdir /static/mule_config 

#RUN poetry install
RUN poetry add glob2
RUN poetry lock && poetry install

RUN chmod +x scripts/fleet_orchestrator.sh
CMD exec scripts/fleet_orchestrator.sh 


