#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
REGISTRY=${REGISTRY:-local}
TAG=${TAG:-0.1.6}
cd "$ROOT_DIR"
docker build -f images/center/Dockerfile -t "$REGISTRY/inference-monitor-center:$TAG" .
docker build --build-arg BASE_IMAGE="${MUSA_BASE_IMAGE:-ubuntu:22.04}" -f images/node-musa/Dockerfile -t "$REGISTRY/inference-monitor-node-musa:$TAG" .
if [[ "${BUILD_NVIDIA:-false}" == "true" ]]; then
  docker build -f images/node-nvidia/Dockerfile -t "$REGISTRY/inference-monitor-node-nvidia:$TAG" .
fi
echo "Built: $REGISTRY/inference-monitor-center:$TAG"
echo "Built: $REGISTRY/inference-monitor-node-musa:$TAG"
[[ "${BUILD_NVIDIA:-false}" != "true" ]] || echo "Built: $REGISTRY/inference-monitor-node-nvidia:$TAG"
