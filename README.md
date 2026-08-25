# Prometheus + Grafana 推理监控产品

最简安装说明请直接阅读：[INSTALL_QUICKSTART.md](INSTALL_QUICKSTART.md)

本 README 面向最终使用者。正式发布包会附带两个已经构建好的 Docker 镜像 tar，用户不需要构建镜像，不需要理解产品源码，也不需要手工配置 Prometheus 或 Grafana。

```text
监控中心：1 个 center 容器（Prometheus + Grafana）
每个节点：1 个 node 容器（node_exporter + GPU exporter）
推理服务：仅提供可访问的 /metrics 地址
```

> 无镜像仓库时，使用离线发布包中的 `images/*.tar`；用户通过 `docker load` 安装，不需要 registry。

## 用户需要准备什么

1. 一台监控中心和若干被监控节点，均已安装 Docker。
2. Prometheus 中心可以访问节点采集端口和推理服务 `/metrics`。
3. 一份 [config/monitoring.yml](config/monitoring.yml)，填写中心地址、节点地址、GPU 类型和 metrics 端口。
4. 从正式离线包取得center镜像，以及与节点硬件匹配的node镜像：

```text
images/inference-monitor-center-<VERSION>.tar
images/inference-monitor-node-musa-<VERSION>.tar
images/inference-monitor-node-nvidia-<VERSION>.tar（NVIDIA节点）
```

产品不处理 SSH、ProxyJump、跳板机、VPN、端口转发或凭据。

## 1. 填写配置

```bash
cp config/monitoring.yml config/monitoring.local.yml
```

只修改模板中标有“需要填写”的字段：

- `platform.public_host`：浏览器访问 Grafana 的中心地址。
- `nodes[].name/address`：节点名称和节点 IP。
- `nodes[].accelerator_vendor`：例如 `musa`。
- `services[].node/port/metrics_path`：外部推理服务 metrics 地址。

生成配置和访问地址：

```bash
python -m pip install -r requirements.txt
python monitorctl.py --config config/monitoring.local.yml render
python monitorctl.py --config config/monitoring.local.yml urls
```

## 2. 运行中心容器

在监控中心执行：

```bash
docker load -i images/inference-monitor-center-<VERSION>.tar

CENTER_IMAGE=inference-monitor-center:<VERSION> \
CONFIG=$PWD/monitoring/generated/prometheus.yml \
./deploy/run-center.sh
```

中心端默认监听 Grafana `3000` 和 Prometheus `9090`。整个集群只运行一个 center 容器。

## 3. 每个节点运行一个 node 容器

在每台 MUSA 节点执行：

```bash
docker load -i images/inference-monitor-node-musa-<VERSION>.tar

NODE_IMAGE=inference-monitor-node-musa:<VERSION> \
./deploy/run-node-musa.sh
```

节点端默认监听 node exporter `9100` 和 MUSA exporter `9500`。如果中心机器也需要被监控，它同时运行 center 和 node 容器。

NVIDIA节点改用：

```bash
docker load -i images/inference-monitor-node-nvidia-<VERSION>.tar
NODE_ENV=$PWD/monitoring/generated/nodes/<节点name>.env \
NODE_IMAGE=inference-monitor-node-nvidia:<VERSION> \
./deploy/run-node-nvidia.sh
```

MUSA MTDCGM和NVIDIA DCGM均默认关闭，只有`monitoring.yml`中对应插件`enabled: true`时才启动并生成Prometheus target。

## 4. 检查并打开看板

```bash
python monitorctl.py --config config/monitoring.local.yml status
python monitorctl.py --config config/monitoring.local.yml urls
```

`urls` 生成 `monitoring/generated/access.json`，包含 Grafana、两个 Dashboard、Prometheus Targets，以及外部推理服务 endpoint。

```text
http://<public_host>:3000/d/inference-system-overview/inference-system-overview
http://<public_host>:3000/d/sglang-detailed-metrics/sglang-detailed-metrics
```

## 停止产品

```bash
./deploy/uninstall.sh
```

默认保留监控数据。

## 用户无需操作的内容

- Prometheus targets 和标签生成
- Grafana datasource 配置
- Dashboard 导入
- recording rules 和告警规则加载
- 多节点数据汇总
- 最终访问地址生成

镜像构建、测试和版本发布见 [开发与发布文档](docs/DEVELOPMENT.md)，不属于普通用户部署流程。
