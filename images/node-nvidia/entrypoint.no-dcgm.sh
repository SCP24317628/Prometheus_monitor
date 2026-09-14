#!/usr/bin/env bash
set -euo pipefail
NODE_PORT=${NODE_EXPORTER_PORT:-9100}
NVIDIA_SMI_PORT=${NVIDIA_SMI_EXPORTER_PORT:-9501}
node_exporter --path.procfs=/host/proc --path.sysfs=/host/sys --path.rootfs=/host/root --web.listen-address="${NODE_EXPORTER_LISTEN_ADDRESS:-0.0.0.0}:${NODE_PORT}" &
node_pid=$!
NVIDIA_SMI_EXPORTER_LISTEN_ADDRESS=${NVIDIA_SMI_EXPORTER_LISTEN_ADDRESS:-0.0.0.0} NVIDIA_SMI_EXPORTER_PORT="$NVIDIA_SMI_PORT" python3 /opt/inference-monitor/nvidia_smi_exporter.py &
smi_pid=$!
cleanup() { kill "$node_pid" "$smi_pid" 2>/dev/null || true; wait || true; }
trap cleanup INT TERM EXIT
while kill -0 "$node_pid" 2>/dev/null && kill -0 "$smi_pid" 2>/dev/null; do sleep 1; done
cleanup
exit 1
