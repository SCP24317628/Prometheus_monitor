#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd); CONFIG=${CONFIG:-"$ROOT_DIR/config/monitoring-only.example.yml"}
cd "$ROOT_DIR"; python3 monitorctl.py --config "$CONFIG" render
args=(); [[ "${INSTALL_CENTER:-0}" == 1 ]] && args+=(--center); [[ "${INSTALL_NODE:-0}" == 1 ]] && args+=(--node)
[[ ${#args[@]} -gt 0 ]] || { echo 'Set INSTALL_CENTER=1 and/or INSTALL_NODE=1' >&2; exit 2; }
python3 monitorctl.py --config "$CONFIG" install "${args[@]}"
