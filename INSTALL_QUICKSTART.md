# 监控产品安装使用手册

本文面向第一次部署的使用者。产品只部署 Prometheus、Grafana 和节点采集器，**不启动、不停止、不修改推理服务**。

## 一、部署结构

```text
监控中心（1 台）
└── inference-monitor-center
    ├── Prometheus :9090
    └── Grafana    :3000

每台被监控机器（1 个）
└── inference-monitor-node-musa 或 inference-monitor-node-nvidia
    ├── node exporter :9100
    ├── GPU exporter  :9500（MUSA）
    └── DCGM exporter :9600（可选，默认关闭）
```

中心 Prometheus 直接抓取每个节点的 exporter，以及用户已经运行的 SGLang
`/metrics` 端点；它不会从 SGLang 日志推算指标。Router 不是默认监控对象。

## 二、用户需要准备

1. 监控中心和节点已安装 Docker；Linux 节点还需要对应的 MUSA/NVIDIA 容器运行时。
2. 中心能够访问每台节点的 `9100`、GPU exporter 端口，以及 SGLang 的 `/metrics` 端口。
3. 浏览器能够访问中心的 `3000` 端口。
4. 与版本号一致的离线镜像包：

```text
images/inference-monitor-center-<VERSION>.tar
images/inference-monitor-node-musa-<VERSION>.tar
images/inference-monitor-node-nvidia-<VERSION>.tar  # 仅 NVIDIA 节点
```

SSH、ProxyJump、跳板机、VPN、端口转发和凭据由用户的网络环境负责；产品不实现这些功能。

## 三、填写配置

在产品目录复制模板：

```bash
cp config/monitoring.yml config/monitoring.local.yml
```

只需要修改以下字段：

```yaml
platform:
  cluster: my-inference-cluster
  environment: production
  public_host: 10.0.0.10       # 浏览器访问 Grafana 的中心 IP
  grafana_port: 3000
  prometheus_port: 9090

nodes:
  - name: prefill-01
    address: 10.0.0.21
    accelerator_vendor: musa   # musa、nvidia 或 none
    plugins:
      node: {enabled: true, metrics_group: performance, port: 9100}
      musa: {enabled: true, metrics_group: performance, port: 9500}
      musa_dcgm: {enabled: false, metrics_group: performance, port: 9600}

services:
  - name: my-prefill
    node: prefill-01
    role: prefill
    port: 23456                  # 已运行 SGLang 的 /metrics 端口
    metrics_path: /metrics
    labels: {model: my-model, deployment: my-pd, version: v1, scenario: production}
```

每增加一台机器复制一个 `nodes` 块；每增加一个 SGLang worker 复制一个
`services` 块。P/D 服务必须分别填写并明确 `role: prefill` 或 `role: decode`。
Router 不需要填写；只有确实需要 Router 入口指标时才作为额外 service 手动登记。

`services[].port` 是 SGLang 已暴露的 Prometheus metrics 端口，不是业务 API 端口。
部署前可从中心验证：

```bash
curl http://<node-ip>:<port>/metrics
```

SGLang 必须启用 metrics；如果端口返回 404、连接拒绝或服务未运行，Grafana
对应卡片会显示无数据，这是数据源状态，不是看板自动生成的数据。

## 四、生成配置（只在中心执行）

```bash
python3 -m pip install -r requirements.txt
python3 monitorctl.py --config config/monitoring.local.yml render
python3 monitorctl.py --config config/monitoring.local.yml urls
```

生成物：

```text
monitoring/generated/prometheus.yml
monitoring/generated/nodes/<节点名>.env
monitoring/generated/access.json
```

`prometheus.yml` 只放在中心；对应节点的 `.env` 文件复制到该节点即可。不要把
密码或私钥复制进产品目录。

## 五、加载镜像

中心：

```bash
docker load -i images/inference-monitor-center-<VERSION>.tar
```

MUSA 节点：

```bash
docker load -i images/inference-monitor-node-musa-<VERSION>.tar
```

NVIDIA 节点改用对应 NVIDIA tar。确认镜像版本与命令中的 `<VERSION>` 完全一致：

```bash
docker images | grep inference-monitor
```

## 六、启动中心（只执行一次）

在中心产品目录执行：

```bash
CENTER_IMAGE=inference-monitor-center:<VERSION> \
CONFIG="$PWD/monitoring/generated/prometheus.yml" \
./deploy/run-center.sh
```

center 会保留数据到 `runtime/prometheus` 和 `runtime/grafana`。如果中心本身也
要采集 CPU/GPU，它同时运行一个 node 容器。

## 七、启动节点（每台执行一次）

把对应 `.env` 文件和 node 镜像 tar 复制到节点，在节点目录执行：

```bash
NODE_IMAGE=inference-monitor-node-musa:<VERSION> \
NODE_ENV="$PWD/monitoring/generated/nodes/<节点名>.env" \
./deploy/run-node-musa.sh
```

NVIDIA 节点：

```bash
NODE_IMAGE=inference-monitor-node-nvidia:<VERSION> \
NODE_ENV="$PWD/monitoring/generated/nodes/<节点名>.env" \
./deploy/run-node-nvidia.sh
```

脚本只会重建名为 `inference-monitor-node` 的本产品容器，不会操作其他容器。

### DCGM 开关

默认关闭：

```yaml
musa_dcgm: {enabled: false, metrics_group: performance, port: 9600}
nvidia_dcgm: {enabled: false, metrics_group: performance, port: 9400}
```

只有宿主已安装对应 DCGM/MTDCGM 并满足运行要求时，才将对应 `enabled` 改为
`true`，重新执行 `render`，再重启该节点容器。MUSA MTDCGM 还要求宿主存在
`dcgmi` 和 `mt-hostengine`。

## 八、验证和访问

中心执行：

```bash
python3 monitorctl.py --config config/monitoring.local.yml status
python3 monitorctl.py --config config/monitoring.local.yml urls
```

最终地址由 `urls` 输出，格式为：

```text
http://<public_host>:3000/d/inference-system-overview/inference-system-overview
```

Prometheus targets 页面：

```text
http://<public_host>:9090/targets
```

排障顺序：先检查目标 endpoint 的 `/metrics`，再看 Prometheus target 是否 UP，
最后检查 Grafana 变量 `cluster`、`node`、`role` 是否选中了目标数据。

## 九、停止和升级

只停止本产品容器：

```bash
./deploy/uninstall.sh
```

该命令默认保留监控数据。升级时加载新版本 tar，使用新版本镜像标签重新执行
启动命令；不要混用不同版本的 center、node 镜像和配置文件。

## 十、产品边界

- Prometheus/Grafana 不会启动或恢复 SGLang 服务。
- 产品不采集 SGLang 日志；日志中的请求 ID、bootstrap、KV transfer 和失败原因
  需要另行接入 Loki/Promtail/Vector 等日志系统。
- 自动端口发现不是 V1 默认行为。端口和 P/D 角色由用户确认后写入配置，避免把
  其他进程或错误的 SGLang 实例纳入监控。
- 用户不需要手工编辑 Prometheus、Grafana datasource、Dashboard 或 recording rules。
