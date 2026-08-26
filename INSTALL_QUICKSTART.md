# Prometheus + Grafana 简洁安装手册

本产品只部署监控，不部署或管理推理服务。

## 组件分工

- `inference-monitor-center:<VERSION>`：一个中心容器，内含 Prometheus + Grafana。整个集群只运行一个。
- `inference-monitor-node-musa:<VERSION>`：一个节点容器，内含 node_exporter + MUSA exporter。每台 MUSA 节点运行一个。

默认端口：

| 组件 | 端口 |
|---|---:|
| Grafana | 3000 |
| Prometheus | 9090 |
| node_exporter | 9100 |
| MUSA exporter | 9500 |
| MTDCGM exporter | 9600 |

## 1. 准备配置

复制模板：

```bash
cp config/monitoring.yml config/monitoring.local.yml
```

只修改以下内容：

```yaml
platform:
  # 浏览器访问 Grafana 的中心机器地址
  public_host: 192.0.2.10

nodes:
  - name: node-01
    # 节点 IP
    address: 192.0.2.10
    accelerator_vendor: musa

services:
  - name: inference-01
    node: node-01
    # 推理服务已经暴露的 metrics 端口
    port: 30000
    metrics_path: /metrics
```

每增加一台节点，就复制一个 `nodes` 块；每增加一个推理实例，就复制一个 `services` 块。

Prometheus 中心必须能访问节点的 `9100/9500` 和推理服务的 `/metrics`。SSH、ProxyJump、跳板机和端口转发由用户网络环境负责，本产品不实现。

## 2. 生成配置

在产品目录执行：

```bash
python -m pip install -r requirements.txt
python monitorctl.py --config config/monitoring.local.yml render
python monitorctl.py --config config/monitoring.local.yml urls
```

生成的文件：

- `monitoring/generated/prometheus.yml`：中心 Prometheus 配置
- `monitoring/generated/access.json`：最终访问地址

## 3. 加载镜像

将两个 tar 文件复制到对应机器，然后执行：

中心机器：

```bash
docker load -i inference-monitor-center-<VERSION>.tar
```

每台 MUSA 节点：

```bash
docker load -i inference-monitor-node-musa-<VERSION>.tar
```

确认镜像：

```bash
docker images | grep inference-monitor
```

## 4. 启动 center 容器

只在监控中心执行一次：

```bash
CENTER_IMAGE=inference-monitor-center:<VERSION> \
CONFIG=$PWD/monitoring/generated/prometheus.yml \
./deploy/run-center.sh
```

center 会启动 Prometheus 和 Grafana，并使用本地目录保存数据：

```text
runtime/prometheus
runtime/grafana
```

## 5. 启动 node 容器

在每台 MUSA 节点执行一次：

```bash
NODE_IMAGE=inference-monitor-node-musa:<VERSION> \
NODE_ENV=$PWD/monitoring/generated/nodes/<节点name>.env \
./deploy/run-node-musa.sh
```

node 容器需要访问宿主机的 `/proc`、`/sys` 和 GPU 设备，因此启动参数包含 host network、host PID、`privileged` 和 MUSA runtime。

DCGM默认关闭。开启MUSA MTDCGM：

```yaml
plugins:
  musa_dcgm:
    enabled: true
    port: 9600
```

重新执行`monitorctl render`后，节点env和Prometheus target会同时更新。MUSA宿主还必须安装MTDCGM并运行`mt-hostengine`。

NVIDIA DCGM同样默认关闭，使用：

```yaml
plugins:
  nvidia_dcgm:
    enabled: true
    port: 9400
```

NVIDIA节点启动：

```bash
NODE_IMAGE=inference-monitor-node-nvidia:<VERSION> \
NODE_ENV=$PWD/monitoring/generated/nodes/<节点name>.env \
./deploy/run-node-nvidia.sh
```

NVIDIA镜像需要NVIDIA Container Toolkit。该变体在NVIDIA硬件验收通过后才能作为正式二进制发布物。

## 6. 验证

```bash
python monitorctl.py --config config/monitoring.local.yml status
python monitorctl.py --config config/monitoring.local.yml urls
```

打开生成的：

```text
http://<public_host>:3000/d/inference-system-overview/inference-system-overview
```

SGLang 详细指标已整合在同一张总览 Dashboard 中，不再单独提供第二个入口。

## 7. 停止

```bash
./deploy/uninstall.sh
```

停止容器不会删除 `runtime/prometheus` 和 `runtime/grafana` 数据。
