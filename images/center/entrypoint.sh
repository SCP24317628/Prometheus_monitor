#!/usr/bin/env sh
set -eu

CONFIG=${PROMETHEUS_CONFIG:-/etc/inference-monitor/prometheus.yml}
DATA=${PROMETHEUS_DATA:-/prometheus}
RETENTION=${PROMETHEUS_RETENTION:-30d}
PROMETHEUS_PORT=${PROMETHEUS_PORT:-9090}

test -r "$CONFIG" || { echo "Missing Prometheus config: $CONFIG" >&2; exit 2; }
mkdir -p "$DATA" /var/lib/grafana/plugins
mkdir -p /var/lib/grafana/dashboards
cp -R /opt/inference-monitor/grafana/dashboards/. /var/lib/grafana/dashboards/ 2>/dev/null || true

prometheus \
  --config.file="$CONFIG" \
  --storage.tsdb.path="$DATA" \
  --storage.tsdb.retention.time="$RETENTION" \
  --web.listen-address="0.0.0.0:$PROMETHEUS_PORT" \
  --web.enable-lifecycle &
prometheus_pid=$!

grafana server --homepath=/usr/share/grafana &
grafana_pid=$!

cleanup() { kill "$prometheus_pid" "$grafana_pid" 2>/dev/null || true; wait || true; }
trap cleanup INT TERM EXIT
wait -n "$prometheus_pid" "$grafana_pid"
exit $?
