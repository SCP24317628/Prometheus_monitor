#!/usr/bin/env python3
"""Prometheus exporter for Moore Threads GPUs via mthreads-gmi JSON output."""

from __future__ import annotations

import json
import math
import os
import re
import subprocess
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Iterable


LISTEN_ADDRESS = os.getenv("MUSA_EXPORTER_LISTEN_ADDRESS", "0.0.0.0")
LISTEN_PORT = int(os.getenv("MUSA_EXPORTER_PORT", "9500"))
COMMAND_TIMEOUT = float(os.getenv("MUSA_EXPORTER_COMMAND_TIMEOUT", "10"))


def _number(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)", str(value))
    if not match:
        return math.nan
    return float(match.group(0))


def _bytes(value: Any) -> float:
    text = str(value).strip()
    number = _number(text)
    units = {
        "kib": 1024,
        "mib": 1024**2,
        "gib": 1024**3,
        "tib": 1024**4,
        "kb": 1000,
        "mb": 1000**2,
        "gb": 1000**3,
        "tb": 1000**4,
    }
    suffix = re.sub(r"[-+\d.\s]", "", text).lower()
    return number * units.get(suffix, 1)


def _escape_label(value: Any) -> str:
    return str(value).replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def _labels(values: dict[str, Any]) -> str:
    body = ",".join(f'{key}="{_escape_label(value)}"' for key, value in values.items())
    return "{" + body + "}"


def _metric(lines: list[str], name: str, help_text: str, kind: str, samples: Iterable[tuple[dict[str, Any], float]]) -> None:
    lines.append(f"# HELP {name} {help_text}")
    lines.append(f"# TYPE {name} {kind}")
    for labels, value in samples:
        if not math.isnan(value):
            lines.append(f"{name}{_labels(labels)} {value:g}")


def _query() -> tuple[dict[str, Any], float]:
    started = time.monotonic()
    process = subprocess.run(
        ["mthreads-gmi", "-q", "--json"],
        capture_output=True,
        check=True,
        text=True,
        timeout=COMMAND_TIMEOUT,
    )
    return json.loads(process.stdout), time.monotonic() - started


def collect() -> str:
    lines: list[str] = []
    started = time.monotonic()
    try:
        document, command_duration = _query()
        devices = document.get("GPU", [])
        driver = document.get("Driver Version", "unknown")
        success = 1.0
    except Exception:
        document, devices, driver, command_duration, success = {}, [], "unknown", 0.0, 0.0

    def device_labels(device: dict[str, Any]) -> dict[str, Any]:
        pci = device.get("PCI", {})
        pci_bus_id = next(
            (value for key, value in pci.items() if key.strip().lower().endswith("bus id")),
            "unknown",
        )
        return {
            "device": device.get("Index", "unknown"),
            "uuid": device.get("GPU UUID", "unknown"),
            "name": device.get("Product Name", "unknown"),
            "pci_bus_id": pci_bus_id,
        }

    _metric(lines, "musa_exporter_scrape_success", "Whether the latest mthreads-gmi scrape succeeded.", "gauge", [({}, success)])
    _metric(lines, "musa_exporter_scrape_duration_seconds", "Time spent collecting one scrape.", "gauge", [({}, time.monotonic() - started)])
    _metric(lines, "musa_exporter_command_duration_seconds", "Time spent running mthreads-gmi.", "gauge", [({}, command_duration)])
    _metric(lines, "musa_attached_gpus", "Number of GPUs reported by mthreads-gmi.", "gauge", [({}, float(len(devices)))])

    info = []
    gpu_util = []
    memory_util = []
    memory_total = []
    memory_used = []
    memory_free = []
    temperature = []
    power = []
    power_limit = []
    graphics_clock = []
    memory_clock = []
    thermal_slowdown = []
    for device in devices:
        labels = device_labels(device)
        info_labels = dict(labels)
        info_labels.update(
            {
                "driver_version": driver,
                "serial": device.get("Serial Number", "unknown"),
                "performance_state": device.get("Performance State", "unknown"),
            }
        )
        info.append((info_labels, 1.0))
        utilization = device.get("Utilization", {})
        memory = device.get("FB Memory Usage", {})
        power_readings = device.get("Power Readings", {})
        clocks = device.get("Clocks", {})
        gpu_util.append((labels, _number(utilization.get("Gpu")) / 100.0))
        memory_util.append((labels, _number(utilization.get("Memory")) / 100.0))
        memory_total.append((labels, _bytes(memory.get("Total"))))
        memory_used.append((labels, _bytes(memory.get("Used"))))
        memory_free.append((labels, _bytes(memory.get("Free"))))
        temperature.append((labels, _number(device.get("Temperature", {}).get("GPU Current Temp"))))
        power.append((labels, _number(power_readings.get("Power Draw "))))
        power_limit.append((labels, _number(power_readings.get("Current Power Limit"))))
        graphics_clock.append((labels, _number(clocks.get("Graphics")) * 1_000_000))
        memory_clock.append((labels, _number(clocks.get("Memory")) * 1_000_000))
        thermal_slowdown.append((labels, _number(device.get("Thermal Slowdown Stats", {}).get("Count"))))

    _metric(lines, "musa_gpu_info", "Static MUSA GPU information.", "gauge", info)
    _metric(lines, "musa_gpu_utilization_ratio", "GPU utilization as a ratio from 0 to 1.", "gauge", gpu_util)
    _metric(lines, "musa_gpu_memory_utilization_ratio", "Device memory utilization as a ratio from 0 to 1.", "gauge", memory_util)
    _metric(lines, "musa_gpu_memory_total_bytes", "Total GPU memory in bytes.", "gauge", memory_total)
    _metric(lines, "musa_gpu_memory_used_bytes", "Used GPU memory in bytes.", "gauge", memory_used)
    _metric(lines, "musa_gpu_memory_free_bytes", "Free GPU memory in bytes.", "gauge", memory_free)
    _metric(lines, "musa_gpu_temperature_celsius", "Current GPU temperature in Celsius.", "gauge", temperature)
    _metric(lines, "musa_gpu_power_watts", "Current GPU power draw in watts.", "gauge", power)
    _metric(lines, "musa_gpu_power_limit_watts", "Current GPU power limit in watts.", "gauge", power_limit)
    _metric(lines, "musa_gpu_graphics_clock_hertz", "Current graphics clock in hertz.", "gauge", graphics_clock)
    _metric(lines, "musa_gpu_memory_clock_hertz", "Current memory clock in hertz.", "gauge", memory_clock)
    _metric(lines, "musa_gpu_thermal_slowdown_total", "Reported thermal slowdown count.", "counter", thermal_slowdown)
    return "\n".join(lines) + "\n"


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path in ("/", "/health"):
            body = b"ok\n"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
        elif self.path == "/metrics":
            body = collect().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
        else:
            body = b"not found\n"
            self.send_response(404)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        return


if __name__ == "__main__":
    ThreadingHTTPServer((LISTEN_ADDRESS, LISTEN_PORT), Handler).serve_forever()
