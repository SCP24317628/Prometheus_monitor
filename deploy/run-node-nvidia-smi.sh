#!/usr/bin/env bash
set -euo pipefail
IMAGE=${NODE_IMAGE:-inference-monitor-node-nvidia:0.1.6}
NODE_ENV=${NODE_ENV:-}
if [[ -n "$NODE_ENV" ]]; then
  [[ -r "$NODE_ENV" ]] || { echo "Node env file not readable: $NODE_ENV" >&2; exit 2; }
  set -a; source "$NODE_ENV"; set +a
fi
docker rm -f inference-monitor-node >/dev/null 2>&1 || true
NVIDIA_SMI_HOST_PATH=${NVIDIA_SMI_HOST_PATH:-/usr/bin/nvidia-smi}
[[ -x "$NVIDIA_SMI_HOST_PATH" ]] || { echo "nvidia-smi not executable: $NVIDIA_SMI_HOST_PATH" >&2; exit 2; }
exec docker run -d --name inference-monitor-node --restart unless-stopped \
  --runtime nvidia --gpus all --network host --pid host \
  -e NODE_EXPORTER_PORT="${NODE_EXPORTER_PORT:-9100}" \
  -e NVIDIA_SMI_EXPORTER_PORT="${NVIDIA_SMI_EXPORTER_PORT:-9501}" \
  -e NVIDIA_SMI_BINARY="${NVIDIA_SMI_BINARY:-/usr/local/bin/nvidia-smi}" \
  -v /proc:/host/proc:ro -v /sys:/host/sys:ro -v /:/host/root:ro,rslave \
  -v "$NVIDIA_SMI_HOST_PATH":/usr/local/bin/nvidia-smi:ro \
  "$IMAGE"
