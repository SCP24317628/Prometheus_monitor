#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
CONFIG=${CONFIG:-"$ROOT_DIR/config/platform.example.yml"}
python3 tools/generate_access.py "$CONFIG" --output "$ROOT_DIR/monitoring/generated/access.json" >/dev/null
python3 - "$ROOT_DIR/monitoring/generated/access.json" <<'PY'
import json, sys, urllib.request
data = json.load(open(sys.argv[1], encoding="utf-8"))
checks = [data["grafana_home"] + "api/health", data["prometheus"] + "-/ready"]
checks += [service["endpoint"] + "/health" for service in data["services"]]
failed = 0
for url in checks:
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            print(f"OK {response.status} {url}")
    except Exception as error:
        failed += 1
        print(f"FAIL {url}: {error}")
raise SystemExit(1 if failed else 0)
PY
