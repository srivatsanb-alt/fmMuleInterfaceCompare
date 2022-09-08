From ubuntu:18.04

RUN apt-get update && apt install -y --no-install-recommends \
    curl unzip git openssh-client \
    python3.7-dev python3-pip && \
    apt-get clean

WORKDIR /app
COPY . /app/
RUN cd /app

RUN python3.7 -m pip install -U pip setuptools wheel && \
    python3.7 -m pip install -U poetry==1.1.12

ARG FM_LOG_DIR

RUN poetry lock && poetry install
RUN chmod +x fleet_orchestrator.sh

RUN mkdir /static
RUN mkdir /app/logs

CMD exec ./fleet_orchestrator.sh 
#> /app/logs/fm_container.log 2>&1 & 
