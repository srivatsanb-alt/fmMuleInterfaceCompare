
FROM grafana/grafana:9.5.2
COPY misc/grafana_config/grafana.ini /etc/grafana/grafana.ini
COPY misc/grafana_config/datasources /etc/grafana/provisioning/datasources
COPY misc/grafana_config/dashboards /etc/grafana/provisioning/dashboards
COPY misc/grafana_config/dashboard_definitions/fleet_analytics.json /var/lib/dashboards/fleet_analytics.json
