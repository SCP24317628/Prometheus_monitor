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


def timeseries(panel_id: int, title: str, targets: list[dict], unit: str | None = None) -> dict:
    defaults = {}
    if unit:
        defaults["unit"] = unit
    return {"id": panel_id, "type": "timeseries", "title": title,
            "gridPos": {"x": 0, "y": 0, "w": 12, "h": 8},
            "datasource": {"type": "prometheus", "uid": "prometheus"},
            "fieldConfig": {"defaults": defaults, "overrides": []},
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

    # Concurrency/queue: trends are more useful than a single current value.
    panels.append(row(100, "SGLang Concurrency & Queue"))
    panels.extend([
        timeseries(101, "Active Requests by Node / Role", [
            target(f"sum by (node,role) (sglang:num_running_reqs{{{FILTER}}})", legend="{{node}} {{role}} running"),
            target(f"sum by (node,role) (sglang:num_prefill_inflight_queue_reqs{{{FILTER}}})", ref="B", legend="{{node}} {{role}} prefill inflight"),
        ], "short"),
        timeseries(102, "Queued Requests by Node / Role", [
            target(f"sum by (node,role) (sglang:num_queue_reqs{{{FILTER}}})", legend="{{node}} {{role}} queued"),
        ], "short"),
    ])
    token_panels = (
        (("Token Throughput by Node / Role", "Token Throughput"), "Token Throughput by Node / Role"),
        (("Generation Throughput & Realtime Tokens by Node / Role", "Generation Throughput and Realtime Tokens"),
         "Generation Throughput & Realtime Tokens by Node / Role"),
    )
    for aliases, output_title in token_panels:
        panel = next((by_title[name] for name in aliases if name in by_title), None)
        if panel:
            panel["title"] = output_title
            panel.setdefault("fieldConfig", {}).setdefault("defaults", {})["unit"] = "suffix: tok/s"
            panels.append(panel)

    # Latency: TTFT and E2E are trends, with mean and tail lines together.  The
    # deployed SGLang exporter has no inter-token latency histogram, so TPOT/
    # ITL cards are intentionally not populated with misleading No-data queries.
    panels.append(row(110, "Latency: TTFT & E2E"))
    panels.extend([
        timeseries(111, "TTFT Trend by Node / Role (Mean / P90 / P99)", [
            target(f"sum by (node,role) (rate(sglang:time_to_first_token_seconds_sum{{{FILTER}}}[5m])) / sum by (node,role) (rate(sglang:time_to_first_token_seconds_count{{{FILTER}}}[5m]))", legend="{{node}} {{role}} mean"),
            target(f"histogram_quantile(0.90, sum by (node,role,le) (rate(sglang:time_to_first_token_seconds_bucket{{{FILTER}}}[5m])))", ref="B", legend="{{node}} {{role}} p90"),
            target(f"histogram_quantile(0.99, sum by (node,role,le) (rate(sglang:time_to_first_token_seconds_bucket{{{FILTER}}}[5m])))", ref="C", legend="{{node}} {{role}} p99"),
        ], "s"),
        timeseries(112, "E2E Trend by Node / Role (Mean / P90 / P99)", [
            target(f"sum by (node,role) (rate(sglang:e2e_request_latency_seconds_sum{{{FILTER}}}[5m])) / sum by (node,role) (rate(sglang:e2e_request_latency_seconds_count{{{FILTER}}}[5m]))", legend="{{node}} {{role}} mean"),
            target(f"histogram_quantile(0.90, sum by (node,role,le) (rate(sglang:e2e_request_latency_seconds_bucket{{{FILTER}}}[5m])))", ref="B", legend="{{node}} {{role}} p90"),
            target(f"histogram_quantile(0.99, sum by (node,role,le) (rate(sglang:e2e_request_latency_seconds_bucket{{{FILTER}}}[5m])))", ref="C", legend="{{node}} {{role}} p99"),
        ], "s"),
    ])
    for title in ("Queue Time p50 / p95", "E2E Latency p50 / p95 / p99", "Per-stage Request Latency p95"):
        if title in by_title:
            panels.append(by_title[title])
    if "Speculative Decode Acceptance" in by_title:
        panels.append(by_title["Speculative Decode Acceptance"])

    # KV cache and PD transfer.
    panels.append(row(120, "KV Cache & PD Transfer"))
    for title in ("SGLang Cache Hit Rate", "Cache and Token Usage", "KV Tokens Available / Used / Evictable",
                  "SWA Pool Tokens", "Mamba Pool Tokens", "PD Queue Depths", "KV Transfer Speed p50 / p95",
                  "KV Transfer Latency p50 / p95", "Bootstrap / Allocation Latency p95", "PD Failures and Retries/s"):
        if title in by_title:
            panels.append(by_title[title])

    # Accelerator and host resources.
    panels.append(row(130, "GPU, CPU & Memory"))
    gpu_utilization = (by_title.get("GPU Utilization (Unified)") or
                       by_title.get("GPU Utilization (MTDCGM)") or
                       timeseries(10, "GPU Utilization (Unified)", [
                           target(f"accelerator_gpu_utilization_ratio{{{NODE_FILTER}}}", legend="{{node}} GPU{{device}}"),
                       ], "percentunit"))
    gpu_utilization["title"] = "GPU Utilization (Unified)"
    panels.append(gpu_utilization)
    for title in ("GPU Memory Used", "Scheduler Utilization / Forward Occupancy",
                  "Capacity and Startup Memory"):
        if title in by_title:
            panels.append(by_title[title])
    panels.extend([
        timeseries(43, "CPU Utilization", [target(f"100 - (avg by (node) (rate(node_cpu_seconds_total{{mode=\"idle\",{NODE_FILTER}}}[5m])) * 100)", legend="{{node}}")], "percent"),
        timeseries(44, "Memory Used", [target(f"node_memory_MemTotal_bytes{{{NODE_FILTER}}} - node_memory_MemAvailable_bytes{{{NODE_FILTER}}}", legend="{{node}}")], "bytes"),
    ])
    # CPU is already expressed as 0..100; bytes lets Grafana render GiB/TiB
    # automatically instead of showing unreadable raw integer byte counts.
    for panel in panels[-2:]:
        if panel["title"] == "CPU Utilization":
            panel["fieldConfig"]["defaults"].update({"min": 0, "max": 100, "decimals": 1})
        elif panel["title"] == "Memory Used":
            panel["fieldConfig"]["defaults"].update({"min": 0, "decimals": 1})

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
