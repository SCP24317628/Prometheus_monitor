#!/usr/bin/env bash
set -euo pipefail
if docker compose version >/dev/null 2>&1; then c=(docker compose); elif command -v docker-compose >/dev/null 2>&1; then c=(docker-compose); else c=(); fi
if [[ ${#c[@]} -gt 0 ]]; then "${c[@]}" -f monitoring/docker-compose.center.yml down; "${c[@]}" -f monitoring/docker-compose.node.yml down; else docker rm -f inference-monitor-center inference-monitor-node inference-monitor-grafana inference-monitor-prometheus inference-monitor-musa-exporter inference-monitor-node-exporter 2>/dev/null || true; fi
echo 'Monitoring containers stopped; named volumes preserved.'
