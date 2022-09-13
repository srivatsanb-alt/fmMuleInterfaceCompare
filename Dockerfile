FROM fleet_manager_base:latest

ENV FM_INSTALL_DIR="/app" REDIS_PORT=6379 FM_PORT=8002   
 
ENV FM_REDIS_URI="redis://localhost:$REDIS_PORT" \
    FM_MAP_DIR="/static" \
    FM_LOG_DIR="/logs" \
    FM_CONFIG_DIR="/static/config/" \
    MULE_ROOT="$FM_INSTALL_DIR/mule" \
    ATI_CONFIG="/static/mule_config/config.toml" \
    ATI_CONSOLIDATED_CONFIG="/static/mule_config/consolidated.toml"

ARG IMAGE_ID
COPY . /app/
RUN mkdir /app/logs
RUN mkdir /static
RUN mkdir /static/mule_config 

RUN cd /app
RUN chmod +x scripts/fleet_orchestrator.sh
CMD exec scripts/fleet_orchestrator.sh 


