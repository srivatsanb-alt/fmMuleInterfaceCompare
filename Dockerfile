From ubuntu:18.04

RUN apt-get update && apt install -y --no-install-recommends \
    curl unzip git openssh-client postgresql-client \
    python3.7-dev python3-pip \
    redis && \
    apt-get clean

WORKDIR /app
COPY . /app/
RUN cd /app
RUN mkdir /app/logs
RUN mkdir /static
RUN mkdir /static/mule_config

RUN python3.7 -m pip install -U pip setuptools wheel && \
    python3.7 -m pip install -U poetry==1.1.12

ENV FM_INSTALL_DIR="/app" REDIS_PORT=6379   
 
ENV FM_REDIS_URI="redis://localhost:$REDIS_PORT" \
    FM_MAP_DIR="$FM_INSTALL_DIR/static/" \
    FM_LOG_DIR="$FM_INSTALL_DIR/logs/" \
    FM_CONFIG_DIR="$FM_INSTALL_DIR/static/config/" \
    MULE_ROOT="$FM_INSTALL_DIR/mule" \
    ATI_CONSOLIDATED_CONFIG="/static/mule_config/consolidated.toml"

RUN echo $FM_LOG_DIR

ARG IMAGE_ID 
RUN poetry lock && poetry install

RUN chmod +x scripts/fleet_orchestrator.sh
CMD exec scripts/fleet_orchestrator.sh 


