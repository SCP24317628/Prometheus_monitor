# Inference Monitoring V1 PRD

## Goal

Provide a portable Prometheus/Grafana platform that shows SGLang request and
token behavior beside CPU, memory, Ethernet, RDMA and accelerator load across
multiple nodes. Operators must be able to move the stack by changing inventory
instead of editing dashboards or hard-coded addresses.

## V1 behavior

- A center Prometheus stores 30 days of metrics and Grafana reads only that
  Prometheus instance.
- Each node exposes selected plugins over HTTP. The product consumes reachable
  metric endpoints; it does not establish SSH tunnels, ProxyJump sessions,
  VPNs, port forwards, or other network paths.
- V1 supports the Prometheus Pull contract. A future Agent/remote_write adapter
  may implement Push without changing labels or dashboards, but that adapter is
  outside this product's V1 implementation.
- `config/monitoring.yml` is the authoritative inventory. It selects
  plugins, metric groups, node addresses and SGLang endpoints.
- Native vendor metrics are preserved. Recording rules create the stable
  `accelerator_*` interface used by cross-hardware dashboards.
- Stable correlation labels are `cluster`, `environment`, `node`, `role`,
  `model`, `deployment`, `version`, `scenario`, `accelerator_vendor` and
  `device`. Request IDs, prompts and free-form errors are rejected as labels.
- Normal collection is 15 seconds. Five-second short analysis mode is a
  configuration change, not a separate deployment.

## Included plugins

- SGLang native `/metrics`
- node_exporter for CPU, memory, filesystem, Ethernet and InfiniBand/RDMA
- MUSA exporter backed by `mthreads-gmi -q --json`
- Optional MUSA MTDCGM exporter, disabled by default
- Optional NVIDIA DCGM exporter interface, disabled by default
- Prometheus self-monitoring

NVIDIA/DCGM is part of the product interface but must pass NVIDIA hardware
validation before a binary image is marked generally available.

## Acceptance criteria

- Prometheus reports every configured target up in a representative deployment.
- SGLang, accelerator, CPU, network and RDMA series are non-empty when enabled.
- Grafana provisions its datasource and dashboards without manual UI steps.
- The config renderer, exporter tests, `promtool`, and dashboard JSON validation pass.

## Out of scope for this iteration

- SSH, ProxyJump, jump-host orchestration, credential management and network
  reachability setup. Users must provide the required network path or manually
  deploy generated node artifacts.
- Public-network exposure, authentication and multi-tenant RBAC
- Logs and distributed traces
- Switch telemetry
- Long-term remote storage
- Automatic bottleneck diagnosis
- Kubernetes/Helm delivery

## Network integration contract

The product has one external integration boundary: a Prometheus-compatible
HTTP metrics endpoint. For each target, the deployment environment must make
`<address>:<port><metrics_path>` reachable from the Prometheus center. How that
reachability is achieved is owned by the user or their network platform.

Manual deployment is supported by copying the product directory or generated
node artifacts to a node and running the node installer locally. The product
does not log into that node or infer a jump path.
