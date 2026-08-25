#!/usr/bin/env bash
set -euo pipefail
node_exporter --path.procfs=/host/proc --path.sysfs=/host/sys --path.rootfs=/host/root --web.listen-address="0.0.0.0:${NODE_EXPORTER_PORT:-9100}" &
node_pid=$!
dcgm_pid=""
if [[ "${NVIDIA_DCGM_ENABLED:-false}" == "true" ]]; then
  dcgm-exporter -a "0.0.0.0:${NVIDIA_DCGM_PORT:-9400}" &
  dcgm_pid=$!
fi
cleanup() { kill "$node_pid" ${dcgm_pid:-} 2>/dev/null || true; wait || true; }
trap cleanup INT TERM EXIT
if [[ -n "$dcgm_pid" ]]; then wait -n "$node_pid" "$dcgm_pid"; else wait "$node_pid"; fi
