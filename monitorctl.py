#!/usr/bin/env python3
"""Single entry point for the portable Prometheus + Grafana product."""
from __future__ import annotations
import argparse, json, pathlib, shutil, subprocess, sys, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip() if (ROOT / "VERSION").exists() else "dev"

def run(command: list[str]) -> None:
    print("$", " ".join(command))
    subprocess.run(command, cwd=ROOT, check=True)

def render(config: pathlib.Path) -> pathlib.Path:
    generated = ROOT / "monitoring" / "generated"
    generated.mkdir(parents=True, exist_ok=True)
    run([sys.executable, "tools/render_config.py", str(config), "--output", str(generated / "prometheus.yml"), "--env-output", str(ROOT / "monitoring" / ".env")])
    run([sys.executable, "tools/generate_access.py", str(config), "--output", str(generated / "access.json")])
    return generated / "access.json"

def compose() -> list[str]:
    if shutil.which("docker-compose"):
        return ["docker-compose"]
    result = subprocess.run(["docker", "compose", "version"], capture_output=True, text=True)
    if result.returncode == 0:
        return ["docker", "compose"]
    raise SystemExit("Docker Compose v2 is required. Install the Docker Compose plugin and retry.")

def urls(config: pathlib.Path) -> None:
    access = json.loads(render(config).read_text(encoding="utf-8"))
    print(json.dumps(access, ensure_ascii=False, indent=2))

def install(config: pathlib.Path, center: bool, node: bool) -> None:
    render(config)
    base = compose()
    if center:
        run(base + ["-f", "monitoring/docker-compose.center.yml", "up", "-d"])
    if node:
        run(base + ["-f", "monitoring/docker-compose.node.yml", "up", "-d"])
    urls(config)

def status(config: pathlib.Path) -> int:
    access = json.loads(render(config).read_text(encoding="utf-8"))
    checks = [("grafana", access["grafana_home"] + "api/health"), ("prometheus", access["prometheus"] + "-/ready")]
    checks.extend((item["name"], item["endpoint"] + "/health") for item in access["services"])
    failed = 0
    for name, url in checks:
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                print(f"OK   {name:20} {response.status} {url}")
        except Exception as error:
            failed += 1
            print(f"FAIL {name:20} {url} ({error})")
    return 1 if failed else 0

def main() -> int:
    parser = argparse.ArgumentParser(prog="monitorctl", description=__doc__)
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    parser.add_argument("--config", type=pathlib.Path, default=ROOT / "config" / "monitoring-only.example.yml")
    sub = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (("render", "validate inventory and render Prometheus config"), ("urls", "print final Grafana, Prometheus and service URLs"), ("status", "check Grafana, Prometheus and service endpoints")):
        sub.add_parser(name, help=help_text)
    install_parser = sub.add_parser("install", help="install center and/or local node stack")
    install_parser.add_argument("--center", action="store_true", help="install Prometheus + Grafana")
    install_parser.add_argument("--node", action="store_true", help="install local node exporters")
    args = parser.parse_args()
    if args.command == "render": render(args.config)
    elif args.command == "urls": urls(args.config)
    elif args.command == "status": return status(args.config)
    elif args.command == "install":
        if not args.center and not args.node: parser.error("install requires --center, --node, or both")
        install(args.config, args.center, args.node)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
