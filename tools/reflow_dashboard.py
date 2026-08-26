#!/usr/bin/env python3
"""Apply the user-facing metric groups and compact comparison layout."""
from __future__ import annotations

import argparse
import copy
import json
import pathlib


PROM = 'cluster=~"$cluster",node=~"$node",role=~"$role"'


def stat(panel_id: int, title: str, expr: str, unit: str = "short") -> dict:
    return {
        "id": panel_id,
        "type": "stat",
        "title": title,
        "gridPos": {"x": 0, "y": 0, "w": 4, "h": 4},
        "datasource": {"type": "prometheus", "uid": "prometheus"},
        "fieldConfig": {"defaults": {"unit": unit}, "overrides": []},
        "options": {"colorMode": "value", "graphMode": "area", "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False}},
        "targets": [{"refId": "A", "expr": expr}],
    }


def row(panel_id: int, title: str) -> dict:
    return {"id": panel_id, "type": "row", "title": title, "gridPos": {"x": 0, "y": 0, "w": 24, "h": 1}, "collapsed": False, "panels": []}


def reflow(path: pathlib.Path) -> dict:
    dashboard = json.loads(path.read_text(encoding="utf-8"))
    by_title = {panel.get("title"): panel for panel in dashboard.get("panels", [])}
    selected = {}
    for title in [
        "Targets Up", "Request Rate", "Generation Tokens/s", "Average GPU Utilization", "Average GPU Memory",
        "SGLang Running and Queued Requests", "Token Throughput", "Time to First Token", "SGLang Cache Hit Rate", "GPU Utilization (MTDCGM)", "GPU Memory Used",
        "Ethernet Throughput", "RDMA Throughput", "HTTP Responses by Status", "Generation Throughput and Realtime Tokens",
        "Prompt Length p50 / p95 / p99", "Generation Length p50 / p95 / p99", "Queue Time p50 / p95", "Per-stage Request Latency p95",
        "E2E Latency p50 / p95 / p99", "Cache and Token Usage", "KV Tokens Available / Used / Evictable", "SWA Pool Tokens", "Mamba Pool Tokens", "PD Queue Depths",
        "KV Transfer Speed p50 / p95", "KV Transfer Latency p50 / p95", "Bootstrap / Allocation Latency p95", "PD Failures and Retries/s",
        "Scheduler Utilization / Forward Occupancy", "Speculative Decode Acceptance", "Capacity and Startup Memory",
    ]:
        if title in by_title:
            selected[title] = by_title[title]

    new_panels = [
        row(100, "SGLang Performance Summary"),
        stat(101, "Running Requests", f"sum({{__name__=\"sglang:num_running_reqs\",{PROM}}})"),
        stat(102, "Prefill Inflight Requests", f"sum({{__name__=\"sglang:num_prefill_inflight_queue_reqs\",{PROM}}})"),
        stat(103, "Queued Requests", f"sum({{__name__=\"sglang:num_queue_reqs\",{PROM}}})"),
        stat(104, "Active HTTP Requests", f"sum({{__name__=\"sglang:http_requests_active\",{PROM}}})"),
        stat(105, "Request Rate", f"sum(rate({{__name__=\"sglang:num_requests_total\",{PROM}}}[5m]))", "reqps"),
        stat(106, "Generation Tokens/s", f"sum(rate({{__name__=\"sglang:generation_tokens_total\",{PROM}}}[5m]))", "short"),
        row(110, "Latency Comparison: TTFT and TPOT"),
        stat(111, "TTFT Mean", f"sum(rate({{__name__=\"sglang:time_to_first_token_seconds_sum\",{PROM}}}[5m])) / sum(rate({{__name__=\"sglang:time_to_first_token_seconds_count\",{PROM}}}[5m]))", "s"),
        stat(112, "TTFT P90", f"histogram_quantile(0.90, sum by (le) (rate({{__name__=\"sglang:time_to_first_token_seconds_bucket\",{PROM}}}[5m])))", "s"),
        stat(113, "TTFT P99", f"histogram_quantile(0.99, sum by (le) (rate({{__name__=\"sglang:time_to_first_token_seconds_bucket\",{PROM}}}[5m])))", "s"),
        stat(114, "TPOT Mean (ITL)", f"sum(rate({{__name__=\"sglang:inter_token_latency_seconds_sum\",{PROM}}}[5m])) / sum(rate({{__name__=\"sglang:inter_token_latency_seconds_count\",{PROM}}}[5m]))", "s"),
        stat(115, "TPOT P90 (ITL)", f"histogram_quantile(0.90, sum by (le) (rate({{__name__=\"sglang:inter_token_latency_seconds_bucket\",{PROM}}}[5m])))", "s"),
        stat(116, "TPOT P99 (ITL)", f"histogram_quantile(0.99, sum by (le) (rate({{__name__=\"sglang:inter_token_latency_seconds_bucket\",{PROM}}}[5m])))", "s"),
        selected["SGLang Running and Queued Requests"],
        selected["Token Throughput"],
        selected["Generation Throughput and Realtime Tokens"],
        row(120, "Latency Detail"),
        selected["Time to First Token"] if "Time to First Token" in by_title else copy.deepcopy(selected["Queue Time p50 / p95"]),
        selected["Queue Time p50 / p95"],
        selected["Per-stage Request Latency p95"],
        selected["SGLang Cache Hit Rate"],
        selected["E2E Latency p50 / p95 / p99"] if "E2E Latency p50 / p95 / p99" in by_title else selected["KV Transfer Latency p50 / p95"],
        row(130, "KV Cache and PD Transfer"),
        selected["Cache and Token Usage"],
        selected["KV Tokens Available / Used / Evictable"],
        selected["SWA Pool Tokens"],
        selected["Mamba Pool Tokens"],
        selected["PD Queue Depths"],
        selected["KV Transfer Speed p50 / p95"],
        selected["KV Transfer Latency p50 / p95"],
        selected["Bootstrap / Allocation Latency p95"],
        selected["PD Failures and Retries/s"],
        row(140, "Accelerator and Network"),
        selected["GPU Utilization (MTDCGM)"],
        selected["GPU Memory Used"],
        selected["RDMA Throughput"],
        selected["Ethernet Throughput"],
        selected["Scheduler Utilization / Forward Occupancy"],
        selected["Speculative Decode Acceptance"],
        selected["Capacity and Startup Memory"],
    ]
    # Preserve only unique panels and assign a compact row-major layout.
    unique = []
    seen = set()
    for panel in new_panels:
        marker = panel.get("id")
        if marker in seen:
            continue
        seen.add(marker); unique.append(panel)
    y = 0; x = 0; row_height = 8
    for panel in unique:
        if panel.get("type") == "row":
            x = 0; panel["gridPos"] = {"x": 0, "y": y, "w": 24, "h": 1}; y += 1
        else:
            width = 4 if panel.get("type") == "stat" else 12
            height = 4 if panel.get("type") == "stat" else 8
            if x + width > 24: x = 0; y += row_height; row_height = height
            panel["gridPos"] = {"x": x, "y": y, "w": width, "h": height}; x += width; row_height = max(row_height, height)
    dashboard["panels"] = unique
    dashboard["title"] = "Inference System Overview"
    dashboard["description"] = "Unified SGLang performance, TTFT/TPOT latency, accelerator, CPU, memory, RDMA and Ethernet monitoring."
    return dashboard


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("input", type=pathlib.Path); parser.add_argument("output", type=pathlib.Path)
    args = parser.parse_args(); result = reflow(args.input); args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"); print(f"reflowed panels={len(result['panels'])}"); return 0


if __name__ == "__main__":
    raise SystemExit(main())
