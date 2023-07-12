FROM fleet_manager_base:dev

ARG FM_IMAGE_INFO
ARG FM_TAG
ARG MULE_IMAGE_ID
ARG FM_SERVER_USERNAME
ARG FM_SERVER_IP
ARG FM_PORT
ARG REDIS_PORT
ARG PLUGIN_PORT

RUN echo "server ip $FM_SERVER_IP"

ENV FM_INSTALL_DIR="/app" REDIS_PORT=$REDIS_PORT FM_PORT=$FM_PORT PLUGIN_PORT=$PLUGIN_PORT FM_SERVER_IP=$FM_SERVER_IP


ENV FM_REDIS_URI="redis://localhost:$REDIS_PORT" \
    FM_STATIC_DIR="/app/static" \
    FM_LOG_DIR="/app/logs" \
    FM_MISC_DIR="/app/misc/" \
    FM_CONFIG_DIR="/app/static/fleet_config/" \
    MULE_ROOT="$FM_INSTALL_DIR/mule" \
    ATI_CONFIG="/app/static/mule_config/config.toml" \
    ATI_CONSOLIDATED_CONFIG="/app/static/mule_config/consolidated.toml" \
    ATI_STATIC_AUTH_USERNAME="ati_static_files" \
    ATI_STATIC_AUTH_PASSWORD="atiStatic112" \
    FM_IMAGE_INFO=$FM_IMAGE_INFO \
    FM_TAG=$FM_TAG \
    FM_SERVER_USERNAME=$FM_SERVER_USERNAME \
    PYTHONPATH="/app" \
    MULE_IMAGE_ID=$MULE_IMAGE_ID

RUN ln -fs /usr/share/zoneinfo/Asia/Kolkata /etc/localtime && \
       dpkg-reconfigure -f noninteractive tzdata

RUN echo "alias inspect='bash /app/scripts/inspect_fm.sh'" >> ~/.bashrc
RUN echo "alias rqi='poetry run rq info'" >> ~/.bashrc
RUN echo "alias rqe='grep -e rq -C 5 /app/logs/fleet_manager.log'"

COPY . /app/
RUN echo "Copying messages_pb2.py to mule/ati/schema on the docker"
COPY ./misc/messages_pb2.py /app/mule/ati/schema/
RUN mkdir /app/logs
RUN cd /app
RUN chmod +x scripts/fleet_orchestrator.sh
CMD exec scripts/fleet_orchestrator.sh
