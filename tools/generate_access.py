#!/usr/bin/env python3
"""Generate user-facing Grafana, Prometheus and service URLs from inventory."""
from __future__ import annotations
import argparse, json, pathlib
import yaml

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=pathlib.Path); parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args(); doc = yaml.safe_load(args.config.read_text(encoding="utf-8")); p = doc["platform"]
    host = p["public_host"]; gp = int(p.get("grafana_port", 3000)); pp = int(p.get("prometheus_port", 9090)); uid = "inference-system-overview"
    access = {"grafana_home": f"http://{host}:{gp}/", "grafana_dashboard": f"http://{host}:{gp}/d/{uid}/inference-system-overview", "prometheus": f"http://{host}:{pp}/", "prometheus_targets": f"http://{host}:{pp}/targets", "cluster": p["cluster"], "environment": p["environment"], "dashboard_uid": uid, "services": []}
    nodes = {n["name"]: n for n in doc.get("nodes", [])}
    for service in doc.get("services", []):
        node = nodes[service["node"]]; endpoint = f"http://{node['address']}:{service['port']}"
        access["services"].append({"name": service["name"], "role": service.get("role", "unknown"), "endpoint": endpoint, "metrics": endpoint + service.get("metrics_path", "/metrics")})
    args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(access, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"); print(access["grafana_dashboard"]); return 0
if __name__ == "__main__": raise SystemExit(main())
