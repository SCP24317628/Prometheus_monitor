# 离线发布包安装说明

本文面向最终用户。离线包必须包含同一个 `<VERSION>` 的源码配置文件和镜像 tar；
不要混用不同版本的 center、node 镜像。

## 1. 网络和机器准备

- 一台中心机器运行一个 `inference-monitor-center`。
- 每台被监控机器运行一个对应硬件的 node 容器。
- 中心可访问节点 `9100`、GPU exporter 端口和已运行 SGLang 的 `/metrics`。
- 用户浏览器可访问中心 `3000`。
- SSH、ProxyJump、VPN 和端口转发由用户处理，产品不管理。

## 2. 配置和生成

在中心解压包并编辑 `config/monitoring.yml`，填写 `public_host`、所有节点
`name/address`、插件开关，以及 SGLang worker 的 metrics `port`、`role` 和标签。
Prefill/Decode 必须显式登记；Router 不属于默认链路。

```bash
python3 -m pip install -r requirements.txt
python3 monitorctl.py --config config/monitoring.yml render
python3 monitorctl.py --config config/monitoring.yml urls
```

生成 `monitoring/generated/prometheus.yml` 和每节点的
`monitoring/generated/nodes/<节点名>.env`。

## 3. 加载和启动中心

```bash
docker load -i images/inference-monitor-center-<VERSION>.tar
CENTER_IMAGE=inference-monitor-center:<VERSION> \
CONFIG="$PWD/monitoring/generated/prometheus.yml" \
./deploy/run-center.sh
```

## 4. 加载和启动节点

将对应 node tar 和该节点 `.env` 复制到节点：

```bash
docker load -i images/inference-monitor-node-musa-<VERSION>.tar
NODE_IMAGE=inference-monitor-node-musa:<VERSION> \
NODE_ENV="$PWD/monitoring/generated/nodes/<节点名>.env" \
./deploy/run-node-musa.sh
```

NVIDIA 节点使用 `inference-monitor-node-nvidia-<VERSION>.tar` 和
`deploy/run-node-nvidia.sh`。

默认 DCGM 关闭；只有显式把配置中的对应插件改为 `enabled: true`，并满足宿主
DCGM/MTDCGM 依赖后才开启。

## 5. 验证和地址

```bash
python3 monitorctl.py --config config/monitoring.yml status
python3 monitorctl.py --config config/monitoring.yml urls
```

Grafana 地址格式：

```text
http://<public_host>:3000/d/inference-system-overview/inference-system-overview
```

完整步骤、端口说明、升级和排障见包内 `INSTALL_QUICKSTART.md`。

本产品抓取的是 `/metrics`，不启动 SGLang、不解析 SGLang 日志；日志采集需要
另行部署 Loki/Promtail/Vector 等系统。
