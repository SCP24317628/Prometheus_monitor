#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
IMAGE=${CENTER_IMAGE:-inference-monitor-center:0.1.5}
CONFIG=${CONFIG:-$ROOT_DIR/monitoring/generated/prometheus.yml}
RULES=${RULES:-$ROOT_DIR/monitoring/prometheus/rules}
DATA=${DATA:-$ROOT_DIR/runtime/prometheus}
GRAFANA_DATA=${GRAFANA_DATA:-$ROOT_DIR/runtime/grafana}
mkdir -p "$DATA" "$GRAFANA_DATA"
docker rm -f inference-monitor-center >/dev/null 2>&1 || true
exec docker run -d --name inference-monitor-center --restart unless-stopped \
  --runtime runc \
  --network host \
  -v "$CONFIG:/etc/inference-monitor/prometheus.yml:ro" \
  -v "$RULES:/etc/prometheus/rules:ro" \
  -v "$DATA:/prometheus" \
  -v "$GRAFANA_DATA:/var/lib/grafana" \
  "$IMAGE"
