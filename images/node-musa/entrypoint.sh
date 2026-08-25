#!/usr/bin/env bash
set -euo pipefail

NODE_PORT=${NODE_EXPORTER_PORT:-9100}
MUSA_PORT=${MUSA_EXPORTER_PORT:-9500}
MTDCGM_PORT=${MTDCGM_EXPORTER_PORT:-9600}
MTDCGM_ENABLED=${MTDCGM_ENABLED:-false}

node_exporter \
  --path.procfs=/host/proc \
  --path.sysfs=/host/sys \
  --path.rootfs=/host/root \
  --web.listen-address="0.0.0.0:${NODE_PORT}" &
node_pid=$!

MUSA_EXPORTER_PORT="$MUSA_PORT" python3 /opt/inference-monitor/musa_exporter.py &
musa_pid=$!

if [[ "$MTDCGM_ENABLED" == "true" && -x /usr/local/mtdcgm/bin/dcgmi ]]; then
  MTDCGM_EXPORTER_PORT="$MTDCGM_PORT" python3 /opt/inference-monitor/mtdcgm_exporter.py &
  mtdcgm_pid=$!
else
  mtdcgm_pid=""
fi

cleanup() { kill "$node_pid" "$musa_pid" ${mtdcgm_pid:-} 2>/dev/null || true; wait || true; }
trap cleanup INT TERM EXIT
if [[ -n "$mtdcgm_pid" ]]; then wait -n "$node_pid" "$musa_pid" "$mtdcgm_pid"; else wait -n "$node_pid" "$musa_pid"; fi
exit $?
