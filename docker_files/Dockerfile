FROM fleet_manager_base:dev

ARG FM_IMAGE_INFO
ARG FM_TAG
ARG GIT_TAGGED
ARG LAST_COMMIT_DT
ARG APP_ENV



ENV FM_INSTALL_DIR="/app" \
    FM_DEV_LOCAL="false" 

ENV FM_STATIC_DIR="/app/static" \
    FM_LOG_DIR="/app/logs" \
    FM_MISC_DIR="/app/misc/" \
    FM_CONFIG_DIR="/app/static/fleet_config/" \
    FM_DOWNLOAD_DIR="/app/downloads" \
    MULE_ROOT="$FM_INSTALL_DIR/mule" \
    ATI_CONFIG="/app/mule_config/config.toml" \
    ATI_CONSOLIDATED_CONFIG="/app/mule_config/consolidated.toml" \
    ATI_STATIC_AUTH_USERNAME="ati_static_files" \
    ATI_STATIC_AUTH_PASSWORD="atiStatic112" \
    FM_IMAGE_INFO=$FM_IMAGE_INFO \
    FM_TAG=$FM_TAG \
    GIT_TAGGED=$GIT_TAGGED \
    LAST_COMMIT_DT=$LAST_COMMIT_DT \
    PYTHONPATH="/app" \
    STATIC_AUTH_FILE="/app/misc/nginx.htpasswd"

RUN ln -fs /usr/share/zoneinfo/Asia/Kolkata /etc/localtime && \
       dpkg-reconfigure -f noninteractive tzdata

RUN echo "alias inspect='bash /app/scripts/inspect_fm.sh'" >> ~/.bashrc
RUN echo "alias rqi='poetry run rq info'" >> ~/.bashrc
RUN echo "alias rqe='grep -e rq -C 5 /app/logs/fleet_manager.log'" >> ~/.bashrc
RUN echo "alias apihw='poetry run python /app/utils/api_key_gen.py --hw_id'" >> ~/.bashrc
RUN echo "alias apind='poetry run python utils/gen_api_keys_n_devices.py --num_devices'" >> ~/.bashrc
RUN echo "alias sip='psql -c \"select sherpas.name, sherpas.ip_address, fleets.name from sherpas join fleets on fleet_id=fleets.id;\"'" >> ~/.bashrc
RUN echo "alias hashpass='poetry run python utils/gen_hashed_password.py --password'" >> ~/.bashrc
RUN echo "alias create_certs='poetry run python utils/create_certs.py --ips'" >> ~/.bashrc


COPY . /app/

RUN if [ "$APP_ENV" != 'dev' ]; then \
    mkdir -p /app/mule_config /app/downloads /app/logs /app/tmp && \
    echo "Copying messages_pb2.py to mule/ati/schema on the docker" && \
    cp /app/misc/messages_pb2.py /app/mule/ati/schema/ && \
    # expose downloads
    cp /app/docs/support_manual.pdf /app/downloads/ && \
    cp /app/misc/FlashTool_SB.tar /app/downloads/ && \
    cp /app/master_fm_comms/mfm_rev_tunnel.tar /app/downloads/; \
    fi


RUN cd /app
RUN chmod +x scripts/fleet_orchestrator.sh
CMD exec scripts/fleet_orchestrator.sh
