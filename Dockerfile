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

RUN cd fleet_manager && \
    poetry lock && poetry install

CMD exec poetry run python3 fleet_orchestrator.py  > /app/out/fm_logs.out 2>&1 
