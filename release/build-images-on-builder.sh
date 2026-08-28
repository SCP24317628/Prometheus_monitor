#!/usr/bin/env bash
set -euo pipefail
VERSION=${VERSION:-$(tr -d '[:space:]' < VERSION)}
OUT=${OUT:-images}
mkdir -p "$OUT"
if [[ -f images/center/prometheus.tar.gz && -f images/center/grafana.tar.gz ]]; then
  docker build -f images/center/Dockerfile.slim -t inference-monitor-center:"$VERSION" .
else
  docker build -f images/center/Dockerfile -t inference-monitor-center:"$VERSION" .
fi
docker build -f images/node-musa/Dockerfile -t inference-monitor-node-musa:"$VERSION" .
docker build -f images/node-nvidia/Dockerfile -t inference-monitor-node-nvidia:"$VERSION" .
docker save inference-monitor-center:"$VERSION" -o "$OUT/inference-monitor-center-$VERSION.tar"
docker save inference-monitor-node-musa:"$VERSION" -o "$OUT/inference-monitor-node-musa-$VERSION.tar"
docker save inference-monitor-node-nvidia:"$VERSION" -o "$OUT/inference-monitor-node-nvidia-$VERSION.tar"
sha256sum "$OUT"/*-"$VERSION".tar > "$OUT/SHA256SUMS"
echo "Created offline image artifacts in $OUT"
