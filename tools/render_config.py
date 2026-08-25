#!/usr/bin/env python3
"""Validate the platform inventory and render a Prometheus configuration."""

from __future__ import annotations

import argparse
import ipaddress
import pathlib
import re
import sys
from typing import Any

import yaml


PLUGIN_JOBS = {"node": 9100, "musa": 9500, "musa_dcgm": 9600, "nvidia_dcgm": 9400}
METRICS_GROUPS = {"core", "performance", "detailed"}
FORBIDDEN_LABELS = {"request_id", "prompt", "input", "output", "error_message", "user"}
LABEL_NAME = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


class ConfigError(ValueError):
    pass


def _required(mapping: dict[str, Any], key: str, context: str) -> Any:
    if key not in mapping or mapping[key] in (None, ""):
        raise ConfigError(f"{context}: missing required field {key!r}")
    return mapping[key]


def _labels(raw: dict[str, Any], context: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for key, value in raw.items():
        if not LABEL_NAME.match(key):
            raise ConfigError(f"{context}: invalid Prometheus label name {key!r}")
        if key in FORBIDDEN_LABELS:
            raise ConfigError(f"{context}: unbounded or sensitive label {key!r} is forbidden")
        if isinstance(value, (dict, list)):
            raise ConfigError(f"{context}: label {key!r} must be a scalar")
        result[key] = str(value)
    return result


def validate(document: dict[str, Any]) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    if document.get("schema_version") != 1:
        raise ConfigError("schema_version must be 1")
    platform = _required(document, "platform", "root")
    _required(platform, "cluster", "platform")
    _required(platform, "environment", "platform")
    for key in ("scrape_interval", "evaluation_interval", "retention"):
        value = str(_required(platform, key, "platform"))
        if not re.match(r"^\d+(?:ms|s|m|h|d|w|y)$", value):
            raise ConfigError(f"platform.{key}: invalid duration {value!r}")

    nodes: dict[str, dict[str, Any]] = {}
    addresses: set[str] = set()
    for index, node in enumerate(document.get("nodes", [])):
        context = f"nodes[{index}]"
        name = str(_required(node, "name", context))
        address = str(_required(node, "address", context))
        if name in nodes:
            raise ConfigError(f"duplicate node name {name!r}")
        if address in addresses:
            raise ConfigError(f"duplicate node address {address!r}")
        try:
            ipaddress.ip_address(address)
        except ValueError as error:
            raise ConfigError(f"{context}: address must be an IP literal: {address!r}") from error
        plugins = node.get("plugins", {})
        unknown = set(plugins) - set(PLUGIN_JOBS)
        if unknown:
            raise ConfigError(f"{context}: unsupported plugins: {', '.join(sorted(unknown))}")
        for plugin_name, plugin in plugins.items():
            group = plugin.get("metrics_group", "core")
            if group not in METRICS_GROUPS:
                raise ConfigError(f"{context}.{plugin_name}: invalid metrics_group {group!r}")
            port = int(plugin.get("port", PLUGIN_JOBS[plugin_name]))
            if not 1 <= port <= 65535:
                raise ConfigError(f"{context}.{plugin_name}: invalid port {port}")
        vendor = str(node.get("accelerator_vendor", "none")).lower()
        musa_dcgm = bool(plugins.get("musa_dcgm", {}).get("enabled", False))
        nvidia_dcgm = bool(plugins.get("nvidia_dcgm", {}).get("enabled", False))
        if musa_dcgm and vendor != "musa":
            raise ConfigError(f"{context}: musa_dcgm requires accelerator_vendor: musa")
        if nvidia_dcgm and vendor != "nvidia":
            raise ConfigError(f"{context}: nvidia_dcgm requires accelerator_vendor: nvidia")
        if musa_dcgm and nvidia_dcgm:
            raise ConfigError(f"{context}: musa_dcgm and nvidia_dcgm cannot both be enabled")
        nodes[name] = node
        addresses.add(address)

    targets: set[tuple[str, int]] = set()
    service_names: set[str] = set()
    for index, service in enumerate(document.get("services", [])):
        context = f"services[{index}]"
        name = str(_required(service, "name", context))
        node_name = str(_required(service, "node", context))
        if name in service_names:
            raise ConfigError(f"duplicate service name {name!r}")
        if node_name not in nodes:
            raise ConfigError(f"{context}: unknown node {node_name!r}")
        port = int(_required(service, "port", context))
        target = (nodes[node_name]["address"], port)
        if target in targets:
            raise ConfigError(f"{context}: duplicate scrape target {target[0]}:{target[1]}")
        _labels(service.get("labels", {}), context)
        targets.add(target)
        service_names.add(name)
    return platform, nodes


def render(document: dict[str, Any]) -> dict[str, Any]:
    platform, nodes = validate(document)
    cluster = str(platform["cluster"])
    environment = str(platform["environment"])
    scrape_configs: list[dict[str, Any]] = [
        {
            "job_name": "prometheus",
            "static_configs": [
                {
                    "targets": ["127.0.0.1:9090"],
                    "labels": {"cluster": cluster, "environment": environment, "source": "prometheus"},
                }
            ],
        }
    ]

    for plugin_name, default_port in PLUGIN_JOBS.items():
        static_configs = []
        for node_name, node in nodes.items():
            plugin = node.get("plugins", {}).get(plugin_name, {})
            if not plugin.get("enabled", False):
                continue
            labels = {
                "cluster": cluster,
                "environment": environment,
                "node": node_name,
                "source": plugin_name,
                "metrics_group": str(plugin.get("metrics_group", "core")),
            }
            if node.get("accelerator_vendor"):
                labels["accelerator_vendor"] = str(node["accelerator_vendor"])
            static_configs.append(
                {
                    "targets": [f"{node['address']}:{int(plugin.get('port', default_port))}"],
                    "labels": labels,
                }
            )
        if static_configs:
            scrape_configs.append({"job_name": plugin_name, "static_configs": static_configs})

    services_by_path: dict[str, list[dict[str, Any]]] = {}
    for service in document.get("services", []):
        node = nodes[service["node"]]
        labels = {
            "cluster": cluster,
            "environment": environment,
            "node": str(service["node"]),
            "role": str(service.get("role", "unknown")),
            "source": "sglang",
        }
        labels.update(_labels(service.get("labels", {}), f"service {service['name']}"))
        path = str(service.get("metrics_path", "/metrics"))
        services_by_path.setdefault(path, []).append(
            {"targets": [f"{node['address']}:{int(service['port'])}"], "labels": labels}
        )
    for index, (path, static_configs) in enumerate(sorted(services_by_path.items())):
        scrape_configs.append(
            {
                "job_name": "sglang" if index == 0 else f"sglang-{index + 1}",
                "metrics_path": path,
                "static_configs": static_configs,
            }
        )

    return {
        "global": {
            "scrape_interval": str(platform["scrape_interval"]),
            "evaluation_interval": str(platform["evaluation_interval"]),
            "external_labels": {"cluster": cluster, "environment": environment},
        },
        "rule_files": ["/etc/prometheus/rules/*.yml"],
        "scrape_configs": scrape_configs,
    }


def render_node_envs(document: dict[str, Any], output_dir: pathlib.Path) -> None:
    _, nodes = validate(document)
    output_dir.mkdir(parents=True, exist_ok=True)
    for old in output_dir.glob("*.env"):
        old.unlink()
    for name, node in nodes.items():
        plugins = node.get("plugins", {})
        lines = [
            f"NODE_NAME={name}",
            f"ACCELERATOR_VENDOR={node.get('accelerator_vendor', 'none')}",
            f"MTDCGM_ENABLED={'true' if plugins.get('musa_dcgm', {}).get('enabled', False) else 'false'}",
            f"MTDCGM_EXPORTER_PORT={int(plugins.get('musa_dcgm', {}).get('port', 9600))}",
            f"NVIDIA_DCGM_ENABLED={'true' if plugins.get('nvidia_dcgm', {}).get('enabled', False) else 'false'}",
            f"NVIDIA_DCGM_PORT={int(plugins.get('nvidia_dcgm', {}).get('port', 9400))}",
        ]
        (output_dir / f"{name}.env").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--env-output", type=pathlib.Path)
    args = parser.parse_args()
    try:
        document = yaml.safe_load(args.config.read_text(encoding="utf-8"))
        rendered = render(document)
    except (OSError, yaml.YAMLError, ConfigError, TypeError, ValueError) as error:
        print(f"configuration error: {error}", file=sys.stderr)
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(yaml.safe_dump(rendered, sort_keys=False), encoding="utf-8", newline="\n")
    render_node_envs(document, args.output.parent / "nodes")
    if args.env_output:
        args.env_output.write_text(
            f"PROMETHEUS_RETENTION={document['platform']['retention']}\n", encoding="utf-8", newline="\n"
        )
    print(f"rendered {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
