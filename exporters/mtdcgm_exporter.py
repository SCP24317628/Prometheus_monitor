#!/usr/bin/env python3
"""Prometheus adapter for Moore Threads MTDCGM dcgmi dmon output."""
from __future__ import annotations
import math, os, re, subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = int(os.getenv("MTDCGM_EXPORTER_PORT", "9600"))
DCGMI = os.getenv("MTDCGM_DCGMI", "/usr/local/mtdcgm/bin/dcgmi")
FIELD_IDS = "203,2002,2003,2005,3100,3101"
FIELD_NAMES = {"203": "gpu_utilization_ratio", "2002": "sm_active_ratio", "2003": "sm_occupancy_ratio", "2005": "dram_active_ratio", "3100": "edc_uncorrectable_total", "3101": "edc_correctable_total"}

def collect() -> str:
    env = os.environ.copy()
    env["PATH"] = "/usr/local/mtdcgm/bin:" + env.get("PATH", "")
    env["LD_LIBRARY_PATH"] = "/usr/local/mtdcgm/lib/x86_64-linux-gnu:/usr/lib:" + env.get("LD_LIBRARY_PATH", "")
    try:
        p = subprocess.run([DCGMI, "dmon", "-e", FIELD_IDS, "-c", "1"], capture_output=True, text=True, timeout=8, env=env, check=True)
        return parse(p.stdout)
    except Exception as exc:
        return "# HELP musa_dcgm_scrape_success Whether MTDCGM collection succeeded.\n# TYPE musa_dcgm_scrape_success gauge\nmusa_dcgm_scrape_success 0\n"

def parse(text: str) -> str:
    lines = ["# HELP musa_dcgm_scrape_success Whether MTDCGM collection succeeded.", "# TYPE musa_dcgm_scrape_success gauge", "musa_dcgm_scrape_success 1"]
    header = next((line for line in text.splitlines() if line.startswith("#Entity")), "")
    if not header:
        lines[-1] = "musa_dcgm_scrape_success 0"
        return "\n".join(lines) + "\n"
    columns = header.split()[1:]
    for line in text.splitlines():
        match = re.match(r"GPU\s+(\d+)\s+(.*)$", line.strip())
        if not match: continue
        device, rest = match.groups(); values = rest.split()
        for index, value in enumerate(values[:len(columns)]):
            field = columns[index]
            field_id = {"GPUTL":"203", "MPACT":"2002", "MPOCC":"2003", "DRAMA":"2005", "MEMEDCUNC":"3100", "MEMEDCCOR":"3101"}.get(field)
            if not field_id or value.upper() == "N/A": continue
            try: number = float(value)
            except ValueError: continue
            name = FIELD_NAMES[field_id]
            if field_id in ("203", "2002", "2003", "2005"): number /= 100.0
            lines += [f"# TYPE musa_dcgm_{name} gauge", f'musa_dcgm_{name}{{device="{device}",field_id="{field_id}"}} {number:g}']
    return "\n".join(lines) + "\n"

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = b"ok\n" if self.path == "/health" else collect().encode() if self.path == "/metrics" else b"not found\n"
        self.send_response(200 if self.path in ("/health", "/metrics") else 404); self.send_header("Content-Type", "text/plain; version=0.0.4"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def log_message(self, *_): return

if __name__ == "__main__": ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
