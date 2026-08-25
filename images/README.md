# Product container images

The preferred runtime is two containers:

```text
inference-monitor-center  Prometheus + Grafana
inference-monitor-node    node_exporter + hardware exporter
```

Build from the repository root with `deploy/build-images.sh`. The center image
contains the Grafana provisioning files and dashboard. Its Prometheus config,
rules, and data directories are mounted at runtime. The MUSA node image uses a
generic Ubuntu base and relies on the host MUSA container runtime for device
capabilities. NVIDIA uses a separate DCGM-based image with the same contract.

MUSA MTDCGM and NVIDIA DCGM are both disabled by default. `monitorctl render`
generates per-node environment files that control whether each exporter starts.

The product does not include SSH, ProxyJump, jump-host handling or credential
management. The user must make the configured metrics endpoints reachable.
