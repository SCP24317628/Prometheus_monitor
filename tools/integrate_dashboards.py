#!/usr/bin/env python3
"""Build one unified Grafana dashboard from the overview and SGLang panels."""
from __future__ import annotations
import argparse, json, pathlib

SKIP_DETAIL_IDS = {2, 3, 4, 8, 11, 16}

def integrate(overview_path: pathlib.Path, detail_path: pathlib.Path) -> dict:
    overview = json.loads(overview_path.read_text(encoding="utf-8"))
    detail = json.loads(detail_path.read_text(encoding="utf-8"))
    bottom = max((p.get("gridPos", {}).get("y", 0) + p.get("gridPos", {}).get("h", 0) for p in overview["panels"]), default=0)
    offset = bottom + 1
    next_id = max((p.get("id", 0) for p in overview["panels"]), default=0) + 1
    for original in detail["panels"]:
        if original.get("id") in SKIP_DETAIL_IDS:
            continue
        panel = json.loads(json.dumps(original))
        panel["id"] = next_id
        next_id += 1
        if "gridPos" in panel:
            panel["gridPos"]["y"] += offset
        overview["panels"].append(panel)
    overview["title"] = "Inference System Overview"
    overview["description"] = "Unified cluster, SGLang, accelerator, CPU, memory, Ethernet and RDMA monitoring."
    overview["tags"] = sorted(set(overview.get("tags", []) + ["sglang", "unified"]))
    return overview

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--overview", type=pathlib.Path, required=True)
    parser.add_argument("--detail", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    result = integrate(args.overview, args.detail)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"integrated panels={len(result['panels'])} output={args.output}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
