#!/usr/bin/env bash
set -euo pipefail
IMAGE=${NODE_IMAGE:-inference-monitor-node-musa:0.1.5}
NODE_ENV=${NODE_ENV:-}
if [[ -n "$NODE_ENV" ]]; then
  [[ -r "$NODE_ENV" ]] || { echo "Node env file not readable: $NODE_ENV" >&2; exit 2; }
  set -a; source "$NODE_ENV"; set +a
fi
MTDCGM_ENABLED=${MTDCGM_ENABLED:-false}
extra_mounts=()
if [[ "$MTDCGM_ENABLED" == "true" ]]; then
  [[ -x /usr/local/mtdcgm/bin/dcgmi ]] || { echo "MTDCGM enabled but /usr/local/mtdcgm/bin/dcgmi is missing" >&2; exit 2; }
  [[ -f /usr/lib/libmtml.so ]] || { echo "MTDCGM enabled but /usr/lib/libmtml.so is missing" >&2; exit 2; }
  extra_mounts+=( -v /usr/local/mtdcgm:/usr/local/mtdcgm:ro -v /usr/lib/libmtml.so:/usr/lib/libmtml.so:ro )
fi
docker rm -f inference-monitor-node >/dev/null 2>&1 || true
exec docker run -d --name inference-monitor-node --restart unless-stopped \
  --runtime mthreads \
  --privileged \
  --network host \
  --pid host \
  -e MTHREADS_VISIBLE_DEVICES=all \
  -e MTHREADS_DRIVER_CAPABILITIES=all \
  -e MTDCGM_ENABLED="$MTDCGM_ENABLED" \
  -v /proc:/host/proc:ro \
  -v /sys:/host/sys:ro \
  -v /:/host/root:ro,rslave \
  -v /run/udev/data:/run/udev/data:ro \
  "${extra_mounts[@]}" \
  "$IMAGE"
