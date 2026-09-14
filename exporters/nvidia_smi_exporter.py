#!/usr/bin/env python3
"""Small Prometheus exporter backed by the host nvidia-smi binary.

This intentionally uses NVML through nvidia-smi and does not require DCGM.
The binary and NVIDIA libraries are supplied by the host/NVIDIA container
runtime; a missing binary is exposed as scrape_success=0 instead of crashing.
"""

from __future__ import annotations

import csv
import math
import os
import re
import subprocess
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Iterable


LISTEN_ADDRESS = os.getenv("NVIDIA_SMI_EXPORTER_LISTEN_ADDRESS", "0.0.0.0")
LISTEN_PORT = int(os.getenv("NVIDIA_SMI_EXPORTER_PORT", "9501"))
COMMAND_TIMEOUT = float(os.getenv("NVIDIA_SMI_EXPORTER_COMMAND_TIMEOUT", "10"))
NVIDIA_SMI_BINARY = os.getenv("NVIDIA_SMI_BINARY", "nvidia-smi")

QUERY_FIELDS = (
    "index,uuid,name,pci.bus_id,driver_version,utilization.gpu,"
    "utilization.memory,memory.total,memory.used,memory.free,temperature.gpu,"
    "power.draw,power.limit,clocks.gr,clocks.mem"
)


def _number(value: Any) -> float:
    match = re.search(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)", str(value))
    return float(match.group(0)) if match else math.nan


def _bytes_mib(value: Any) -> float:
    number = _number(value)
    return number * 1024**2 if not math.isnan(number) else number


def _escape(value: Any) -> str:
    return str(value).replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def _labels(values: dict[str, Any]) -> str:
    return "{" + ",".join(f'{k}="{_escape(v)}"' for k, v in values.items()) + "}"


def _metric(lines: list[str], name: str, help_text: str, kind: str, samples: Iterable[tuple[dict[str, Any], float]]) -> None:
    lines.extend((f"# HELP {name} {help_text}", f"# TYPE {name} {kind}"))
    for labels, value in samples:
        if not math.isnan(value):
            lines.append(f"{name}{_labels(labels)} {value:g}")


def _query() -> tuple[list[dict[str, str]], float]:
    started = time.monotonic()
    process = subprocess.run(
        [NVIDIA_SMI_BINARY, f"--query-gpu={QUERY_FIELDS}", "--format=csv,noheader,nounits"],
        capture_output=True,
        check=True,
        text=True,
        timeout=COMMAND_TIMEOUT,
    )
    rows = []
    for values in csv.reader(process.stdout.splitlines(), skipinitialspace=True):
        if len(values) != 15:
            continue
        rows.append(dict(zip(QUERY_FIELDS.split(","), (v.strip() for v in values))))
    return rows, time.monotonic() - started


def collect() -> str:
    lines: list[str] = []
    started = time.monotonic()
    try:
        devices, command_duration = _query()
        success = 1.0
    except Exception:
        devices, command_duration, success = [], 0.0, 0.0

    _metric(lines, "nvidia_smi_exporter_scrape_success", "Whether the latest nvidia-smi scrape succeeded.", "gauge", [({}, success)])
    _metric(lines, "nvidia_smi_exporter_scrape_duration_seconds", "Time spent collecting one scrape.", "gauge", [({}, time.monotonic() - started)])
    _metric(lines, "nvidia_smi_exporter_command_duration_seconds", "Time spent running nvidia-smi.", "gauge", [({}, command_duration)])
    _metric(lines, "nvidia_attached_gpus", "Number of GPUs reported by nvidia-smi.", "gauge", [({}, float(len(devices)))])

    info, gpu_util, memory_util, memory_total, memory_used, memory_free = [], [], [], [], [], []
    temperature, power, power_limit, graphics_clock, memory_clock = [], [], [], [], []
    for device in devices:
        labels = {
            "device": device.get("index", "unknown"),
            "uuid": device.get("uuid", "unknown"),
            "name": device.get("name", "unknown"),
            "pci_bus_id": device.get("pci.bus_id", "unknown"),
        }
        info.append((dict(labels, driver_version=device.get("driver_version", "unknown")), 1.0))
        gpu_util.append((labels, _number(device.get("utilization.gpu")) / 100.0))
        memory_util.append((labels, _number(device.get("utilization.memory")) / 100.0))
        memory_total.append((labels, _bytes_mib(device.get("memory.total"))))
        memory_used.append((labels, _bytes_mib(device.get("memory.used"))))
        memory_free.append((labels, _bytes_mib(device.get("memory.free"))))
        temperature.append((labels, _number(device.get("temperature.gpu"))))
        power.append((labels, _number(device.get("power.draw"))))
        power_limit.append((labels, _number(device.get("power.limit"))))
        graphics_clock.append((labels, _number(device.get("clocks.gr")) * 1_000_000))
        memory_clock.append((labels, _number(device.get("clocks.mem")) * 1_000_000))

    _metric(lines, "nvidia_gpu_info", "Static NVIDIA GPU information from nvidia-smi.", "gauge", info)
    _metric(lines, "nvidia_gpu_utilization_ratio", "GPU utilization as a ratio from 0 to 1.", "gauge", gpu_util)
    _metric(lines, "nvidia_gpu_memory_utilization_ratio", "Device memory utilization as a ratio from 0 to 1.", "gauge", memory_util)
    _metric(lines, "nvidia_gpu_memory_total_bytes", "Total GPU memory in bytes.", "gauge", memory_total)
    _metric(lines, "nvidia_gpu_memory_used_bytes", "Used GPU memory in bytes.", "gauge", memory_used)
    _metric(lines, "nvidia_gpu_memory_free_bytes", "Free GPU memory in bytes.", "gauge", memory_free)
    _metric(lines, "nvidia_gpu_temperature_celsius", "Current GPU temperature in Celsius.", "gauge", temperature)
    _metric(lines, "nvidia_gpu_power_watts", "Current GPU power draw in watts.", "gauge", power)
    _metric(lines, "nvidia_gpu_power_limit_watts", "Current GPU power limit in watts.", "gauge", power_limit)
    _metric(lines, "nvidia_gpu_graphics_clock_hertz", "Current graphics clock in hertz.", "gauge", graphics_clock)
    _metric(lines, "nvidia_gpu_memory_clock_hertz", "Current memory clock in hertz.", "gauge", memory_clock)
    return "\n".join(lines) + "\n"


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path in ("/", "/health"):
            body, content_type, status = b"ok\n", "text/plain; charset=utf-8", 200
        elif self.path == "/metrics":
            body, content_type, status = collect().encode(), "text/plain; version=0.0.4; charset=utf-8", 200
        else:
            body, content_type, status = b"not found\n", "text/plain; charset=utf-8", 404
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        return


if __name__ == "__main__":
    ThreadingHTTPServer((LISTEN_ADDRESS, LISTEN_PORT), Handler).serve_forever()
