#!/usr/bin/env python3
"""Build the single user-facing dashboard with explicit metric categories."""
from __future__ import annotations

import argparse
import copy
import json
import pathlib


FILTER = 'cluster=~"$cluster",node=~"$node",role=~"$role"'
NODE_FILTER = 'cluster=~"$cluster",node=~"$node"'


def row(panel_id: int, title: str) -> dict:
    return {"id": panel_id, "type": "row", "title": title,
            "gridPos": {"x": 0, "y": 0, "w": 24, "h": 1},
            "collapsed": False, "panels": []}


def stat(panel_id: int, title: str, expr: str, unit: str = "short") -> dict:
    return {
        "id": panel_id, "type": "stat", "title": title,
        "gridPos": {"x": 0, "y": 0, "w": 4, "h": 4},
        "datasource": {"type": "prometheus", "uid": "prometheus"},
        "fieldConfig": {"defaults": {"unit": unit, "decimals": 2}, "overrides": []},
        "options": {"colorMode": "value", "graphMode": "area",
                     "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False}},
        "targets": [{"refId": "A", "expr": expr}],
    }


def timeseries(panel_id: int, title: str, targets: list[dict]) -> dict:
    return {"id": panel_id, "type": "timeseries", "title": title,
            "gridPos": {"x": 0, "y": 0, "w": 12, "h": 8},
            "datasource": {"type": "prometheus", "uid": "prometheus"},
            "fieldConfig": {"defaults": {}, "overrides": []},
            "options": {"legend": {"displayMode": "table", "placement": "bottom", "calcs": ["lastNotNull"]}},
            "targets": targets}


def target(expr: str, ref: str = "A", legend: str = "") -> dict:
    value = {"refId": ref, "expr": expr}
    if legend:
        value["legendFormat"] = legend
    return value


def reflow(path: pathlib.Path) -> dict:
    dashboard = json.loads(path.read_text(encoding="utf-8"))
    by_title = {p.get("title"): copy.deepcopy(p) for p in dashboard.get("panels", [])
                if p.get("type") != "row" and p.get("id", 0) < 100}
    panels: list[dict] = []

    # Concurrency/queue: only request-state and throughput cards.
    panels.append(row(100, "SGLang Concurrency & Queue"))
    panels.extend([
        stat(101, "Running Requests", f"sum(sglang:num_running_reqs{{{FILTER}}})"),
        stat(102, "Prefill Inflight Requests", f"sum(sglang:num_prefill_inflight_queue_reqs{{{FILTER}}})"),
        stat(103, "Queued Requests", f"sum(sglang:num_queue_reqs{{{FILTER}}})"),
        stat(104, "Generation Throughput", f"sum(sglang:gen_throughput{{{FILTER}}})", "tokps"),
    ])
    for title in ("SGLang Running and Queued Requests", "Token Throughput", "Generation Throughput and Realtime Tokens"):
        if title in by_title:
            panels.append(by_title[title])

    # Latency: TTFT and E2E cards are adjacent and identically sized.  The
    # deployed SGLang exporter has no inter-token latency histogram, so TPOT/
    # ITL cards are intentionally not populated with misleading No-data queries.
    panels.append(row(110, "Latency: TTFT & E2E"))
    panels.extend([
        stat(111, "TTFT Mean", f"sum(rate(sglang:time_to_first_token_seconds_sum{{{FILTER}}}[5m])) / sum(rate(sglang:time_to_first_token_seconds_count{{{FILTER}}}[5m]))", "s"),
        stat(112, "TTFT P90", f"histogram_quantile(0.90, sum by (le) (rate(sglang:time_to_first_token_seconds_bucket{{{FILTER}}}[5m])))", "s"),
        stat(113, "TTFT P99", f"histogram_quantile(0.99, sum by (le) (rate(sglang:time_to_first_token_seconds_bucket{{{FILTER}}}[5m])))", "s"),
        stat(114, "E2E Mean", f"sum(rate(sglang:e2e_request_latency_seconds_sum{{{FILTER}}}[5m])) / sum(rate(sglang:e2e_request_latency_seconds_count{{{FILTER}}}[5m]))", "s"),
        stat(115, "E2E P90", f"histogram_quantile(0.90, sum by (le) (rate(sglang:e2e_request_latency_seconds_bucket{{{FILTER}}}[5m])))", "s"),
        stat(116, "E2E P99", f"histogram_quantile(0.99, sum by (le) (rate(sglang:e2e_request_latency_seconds_bucket{{{FILTER}}}[5m])))", "s"),
    ])
    for title in ("Time to First Token", "Queue Time p50 / p95", "E2E Latency p50 / p95 / p99", "Per-stage Request Latency p95"):
        if title in by_title:
            panels.append(by_title[title])

    # KV cache and PD transfer.
    panels.append(row(120, "KV Cache & PD Transfer"))
    for title in ("SGLang Cache Hit Rate", "Cache and Token Usage", "KV Tokens Available / Used / Evictable",
                  "SWA Pool Tokens", "Mamba Pool Tokens", "PD Queue Depths", "KV Transfer Speed p50 / p95",
                  "KV Transfer Latency p50 / p95", "Bootstrap / Allocation Latency p95", "PD Failures and Retries/s"):
        if title in by_title:
            panels.append(by_title[title])

    # Accelerator and host resources.
    panels.append(row(130, "GPU, CPU & Memory"))
    for title in ("GPU Utilization (MTDCGM)", "GPU Memory Used", "Scheduler Utilization / Forward Occupancy",
                  "Speculative Decode Acceptance", "Capacity and Startup Memory"):
        if title in by_title:
            panel = by_title[title]
            if title == "GPU Utilization (MTDCGM)":
                panel["title"] = "GPU Utilization (Unified)"
            panels.append(panel)
    panels.extend([
        timeseries(43, "CPU Utilization", [target(f"100 - (avg by (node) (rate(node_cpu_seconds_total{{mode=\"idle\",{NODE_FILTER}}}[5m])) * 100)", legend="{{node}}")]),
        timeseries(44, "Memory Used", [target(f"node_memory_MemTotal_bytes{{{NODE_FILTER}}} - node_memory_MemAvailable_bytes{{{NODE_FILTER}}}", legend="{{node}}")]),
    ])

    # RDMA is intentionally before Ethernet.  The exporter exposes bytes/s,
    # not physical link capacity, so no fabricated percentage is shown.
    panels.append(row(140, "Network: RDMA First"))
    for title in ("RDMA Throughput", "Ethernet Throughput"):
        if title in by_title:
            panels.append(by_title[title])

    # Deterministic row-major placement. All cards in a group share dimensions.
    y = 0
    x = 0
    current_height = 1
    for panel in panels:
        if panel.get("type") == "row":
            if x:
                y += current_height
            x = 0
            current_height = 1
            panel["gridPos"] = {"x": 0, "y": y, "w": 24, "h": 1}
            y += 1
            continue
        width = 4 if panel.get("type") == "stat" else 12
        height = 4 if panel.get("type") == "stat" else 8
        if x + width > 24:
            y += current_height
            x = 0
            current_height = height
        panel["gridPos"] = {"x": x, "y": y, "w": width, "h": height}
        x += width
        current_height = max(current_height, height)
    dashboard["panels"] = panels
    dashboard["title"] = "Inference System Overview"
    dashboard["description"] = (
        "Unified SGLang concurrency, TTFT/E2E latency, KV/PD, GPU, CPU, memory and network monitoring. "
        "TPOT/ITL percentiles require an inter-token latency histogram from the SGLang exporter; "
        "RDMA utilization requires link-capacity telemetry in addition to the exposed bytes/s rate."
    )
    return dashboard


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=pathlib.Path)
    parser.add_argument("output", type=pathlib.Path)
    args = parser.parse_args()
    result = reflow(args.input)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"reflowed panels={len(result['panels'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
