#!/usr/bin/env bash
set -euo pipefail
CONFIG=${PROMETHEUS_CONFIG:-/etc/inference-monitor/prometheus.yml}
DATA=${PROMETHEUS_DATA:-/prometheus}
mkdir -p "$DATA" /var/lib/grafana/plugins /var/lib/grafana/dashboards
cp -R /opt/inference-monitor/grafana/dashboards/. /var/lib/grafana/dashboards/ 2>/dev/null || true
prometheus --config.file="$CONFIG" --storage.tsdb.path="$DATA" --storage.tsdb.retention.time="${PROMETHEUS_RETENTION:-30d}" --web.listen-address="0.0.0.0:${PROMETHEUS_PORT:-9090}" --web.enable-lifecycle &
prometheus_pid=$!
grafana server --homepath=/opt/grafana &
grafana_pid=$!
cleanup() { kill "$prometheus_pid" "$grafana_pid" 2>/dev/null || true; wait || true; }
trap cleanup INT TERM EXIT
wait -n "$prometheus_pid" "$grafana_pid"
