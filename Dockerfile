FROM fleet_manager_base:dev

ARG FM_IMAGE_INFO
ARG MULE_IMAGE_ID
ARG HOSTNAME
ENV FM_INSTALL_DIR="/app" REDIS_PORT=6379 FM_PORT=8002

ENV FM_REDIS_URI="redis://localhost:$REDIS_PORT" \
    FM_MAP_DIR="/app/static" \
    FM_LOG_DIR="/app/logs" \
    FM_CONFIG_DIR="/app/static/fleet_config/" \
    MULE_ROOT="$FM_INSTALL_DIR/mule" \
    ATI_CONFIG="/app/static/mule_config/config.toml" \
    ATI_CONSOLIDATED_CONFIG="/app/static/mule_config/consolidated.toml" \
    FM_IMAGE_INFO=$FM_IMAGE_INFO \
    HOSTNAME=$HOSTNAME \
    MULE_IMAGE_ID=$MULE_IMAGE_ID

RUN ln -fs /usr/share/zoneinfo/Asia/Kolkata /etc/localtime && \
       dpkg-reconfigure -f noninteractive tzdata

COPY . /app/
RUN echo "Copying messages_pb2.py to mule/ati/schema on the docker"
COPY ./static/messages_pb2.py /app/mule/ati/schema/
RUN mkdir /app/logs
RUN cd /app
RUN chmod +x scripts/fleet_orchestrator.sh
CMD exec scripts/fleet_orchestrator.sh
