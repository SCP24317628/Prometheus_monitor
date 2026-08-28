#!/usr/bin/env bash
set -euo pipefail
IMAGE=${NODE_IMAGE:-inference-monitor-node-nvidia:0.1.5}
NODE_ENV=${NODE_ENV:-}
if [[ -n "$NODE_ENV" ]]; then
  [[ -r "$NODE_ENV" ]] || { echo "Node env file not readable: $NODE_ENV" >&2; exit 2; }
  set -a; source "$NODE_ENV"; set +a
fi
NVIDIA_DCGM_ENABLED=${NVIDIA_DCGM_ENABLED:-false}
docker rm -f inference-monitor-node >/dev/null 2>&1 || true
exec docker run -d --name inference-monitor-node --restart unless-stopped \
  --runtime nvidia --gpus all --network host --pid host \
  -e NVIDIA_DCGM_ENABLED="$NVIDIA_DCGM_ENABLED" \
  -v /proc:/host/proc:ro -v /sys:/host/sys:ro -v /:/host/root:ro,rslave -v /run/udev/data:/run/udev/data:ro \
  "$IMAGE"
