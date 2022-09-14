FROM fleet_manager_base:latest

ENV FM_INSTALL_DIR="/app" REDIS_PORT=6379 FM_PORT=8002   
 
ENV FM_REDIS_URI="redis://localhost:$REDIS_PORT" \
    FM_MAP_DIR="/app/static" \
    FM_LOG_DIR="/app/logs" \
    FM_CONFIG_DIR="/app/static/fleet_config/" \
    MULE_ROOT="$FM_INSTALL_DIR/mule" \
    ATI_CONFIG="/app/static/mule_config/config.toml" \
    ATI_CONSOLIDATED_CONFIG="/app/static/mule_config/consolidated.toml"

ARG IMAGE_ID
COPY . /app/

RUN mkdir /app/logs
RUN cd /app
RUN chmod +x scripts/fleet_orchestrator.sh
CMD exec scripts/fleet_orchestrator.sh 


