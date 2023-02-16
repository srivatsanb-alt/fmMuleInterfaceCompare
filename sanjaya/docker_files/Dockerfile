From sanjaya:base
WORKDIR /app
COPY . /app

RUN mkdir /app/logs
RUN chmod +x /app/scripts/orchestrator.sh
CMD exec bash /app/scripts/orchestrator.sh
