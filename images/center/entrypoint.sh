#!/usr/bin/env sh
set -u

PROMETHEUS_CONFIG=${PROMETHEUS_CONFIG:-/etc/inference-monitor/prometheus.yml}
PROMETHEUS_STORAGE_PATH=${PROMETHEUS_STORAGE_PATH:-/prometheus}
PROMETHEUS_RETENTION_TIME=${PROMETHEUS_RETENTION_TIME:-15d}
PROMETHEUS_LISTEN_ADDRESS=${PROMETHEUS_LISTEN_ADDRESS:?PROMETHEUS_LISTEN_ADDRESS must be explicitly configured, for example 10.0.0.10:9090}

if [ -n "${PROMETHEUS_BIN:-}" ]; then
  prometheus_bin=$PROMETHEUS_BIN
elif command -v prometheus >/dev/null 2>&1; then
  prometheus_bin=$(command -v prometheus)
elif [ -x /opt/prometheus/prometheus ]; then
  prometheus_bin=/opt/prometheus/prometheus
elif [ -x /usr/local/bin/prometheus ]; then
  prometheus_bin=/usr/local/bin/prometheus
else
  echo "Prometheus binary was not found" >&2
  exit 64
fi
if [ ! -r "$PROMETHEUS_CONFIG" ]; then
  echo "Prometheus config is not readable: $PROMETHEUS_CONFIG" >&2
  exit 64
fi

if [ -n "${GRAFANA_BIN:-}" ]; then
  grafana_bin=$GRAFANA_BIN
  grafana_mode=${GRAFANA_MODE:-server}
elif command -v grafana-server >/dev/null 2>&1; then
  grafana_bin=$(command -v grafana-server)
  grafana_mode=legacy
elif command -v grafana >/dev/null 2>&1; then
  grafana_bin=$(command -v grafana)
  grafana_mode=server
elif [ -x /usr/share/grafana/bin/grafana ]; then
  grafana_bin=/usr/share/grafana/bin/grafana
  grafana_mode=server
else
  echo "Grafana binary was not found" >&2
  exit 64
fi

grafana_home=${GF_PATHS_HOME:-}
if [ -z "$grafana_home" ]; then
  for candidate in /usr/share/grafana /opt/grafana; do
    if [ -d "$candidate" ]; then grafana_home=$candidate; break; fi
  done
fi
if [ -z "$grafana_home" ] || [ ! -d "$grafana_home" ]; then
  echo "Grafana home path is not a directory: ${grafana_home:-unset}" >&2
  exit 64
fi

prom_pid=
grafana_pid=
stopping=0

stop_children() {
  stopping=1
  trap - INT TERM
  [ -n "$prom_pid" ] && kill -TERM "$prom_pid" 2>/dev/null || true
  [ -n "$grafana_pid" ] && kill -TERM "$grafana_pid" 2>/dev/null || true
  [ -n "$prom_pid" ] && wait "$prom_pid" 2>/dev/null || true
  [ -n "$grafana_pid" ] && wait "$grafana_pid" 2>/dev/null || true
}

on_signal() { stop_children; exit 143; }
trap on_signal INT TERM

"$prometheus_bin" \
  --config.file="$PROMETHEUS_CONFIG" \
  --storage.tsdb.path="$PROMETHEUS_STORAGE_PATH" \
  --storage.tsdb.retention.time="$PROMETHEUS_RETENTION_TIME" \
  --web.listen-address="$PROMETHEUS_LISTEN_ADDRESS" &
prom_pid=$!

if [ "$grafana_mode" = legacy ]; then
  "$grafana_bin" --homepath="$grafana_home" &
else
  "$grafana_bin" server --homepath="$grafana_home" &
fi
grafana_pid=$!

# POSIX sh has no portable `wait -n`.
while kill -0 "$prom_pid" 2>/dev/null && kill -0 "$grafana_pid" 2>/dev/null; do sleep 1; done

status=1
if ! kill -0 "$prom_pid" 2>/dev/null; then wait "$prom_pid" || status=$?; else wait "$grafana_pid" || status=$?; fi
if [ "$stopping" -eq 0 ]; then stop_children; fi
exit "$status"
