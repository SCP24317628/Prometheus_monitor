#!/usr/bin/env bash
set -euo pipefail
NODE_PORT=${NODE_EXPORTER_PORT:-9100}
MUSA_PORT=${MUSA_EXPORTER_PORT:-9500}
node_exporter --path.procfs=/host/proc --path.sysfs=/host/sys --path.rootfs=/host/root --web.listen-address="${NODE_EXPORTER_LISTEN_ADDRESS:-0.0.0.0}:${NODE_PORT}" &
node_pid=$!
MUSA_EXPORTER_LISTEN_ADDRESS=${MUSA_EXPORTER_LISTEN_ADDRESS:-0.0.0.0} MUSA_EXPORTER_PORT="$MUSA_PORT" python3 /opt/inference-monitor/musa_exporter.py &
musa_pid=$!
cleanup() { kill "$node_pid" "$musa_pid" 2>/dev/null || true; wait || true; }
trap cleanup INT TERM EXIT
while kill -0 "$node_pid" 2>/dev/null && kill -0 "$musa_pid" 2>/dev/null; do sleep 1; done
cleanup
exit 1
