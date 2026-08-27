# Inference Monitoring V1 PRD

## Goal

Provide a portable Prometheus/Grafana platform that shows SGLang Prefill and
Decode request/token behavior beside CPU, memory, Ethernet, RDMA and
accelerator load across multiple nodes. Operators must be able to move the
stack by changing inventory instead of editing dashboards or hard-coded
addresses. The Router is not part of the default monitoring chain.

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
  plugins, metric groups, node addresses and SGLang Prefill/Decode endpoints.
- SGLang service ports and roles are explicit configuration inputs. V1 does not
  automatically adopt arbitrary open ports. A future discovery mode may report
  candidates, but a user must confirm model, deployment and Prefill/Decode role
  before a target is added.
- A deployment may contain multiple Prefill and/or Decode workers. Each worker
  is an independent Prometheus target, even when several workers share the same
  metrics port number. The `role` label is mandatory for latency and queue
  comparisons; the product must never infer P/D role from the port number.
- Diagnostic charts must preserve `node` and `role` in both PromQL aggregation
  and legends. Cluster-wide sums may be offered as an explicit overview, but
  must not replace per-worker lines used for bottleneck localization.
- Request concurrency and queued requests are separate trends. Active requests
  include running requests and Prefill inflight requests; queue depth is shown
  independently so users can distinguish service concurrency from backlog.
- Token throughput is displayed as `tok/s`. It must not be labeled TOPS or
  TFLOPS: GPU floating-point throughput requires hardware FLOP counters that
  are not exposed by the current SGLang/MUSA exporters.
- Speculative decoding is displayed in two adjacent trends: draft-token count
  together with accepted length, and acceptance rate in a separate percentage
  chart. All three series retain `node` and `role` for worker-level diagnosis.
- Router metrics are optional integration data (health, ingress and routing
  errors when the Router exposes them); they are not required for worker
  latency, queue, KV, GPU or RDMA metrics and are not provisioned by default.
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

## Logs and Router boundary

The Prometheus product consumes SGLang `/metrics`; it does not parse SGLang or
Router logs. Request IDs, bootstrap details, KV-transfer diagnostics and
failure explanations require a separate log collector (for example
Promtail/Vector plus Loki) with explicit container/path and role metadata.
Port discovery cannot replace log collection.

Router scraping is an optional target. Removing the Router target does not stop
the Router process; it only prevents Router-level ingress metrics from being
stored. Prefill and Decode targets remain the source of worker performance and
latency metrics.

## Out of scope for this iteration

- SSH, ProxyJump, jump-host orchestration, credential management and network
  reachability setup. Users must provide the required network path or manually
  deploy generated node artifacts.
- Public-network exposure, authentication and multi-tenant RBAC
- SGLang/Router log collection and distributed traces (reserved for a separate
  logging plugin)
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
