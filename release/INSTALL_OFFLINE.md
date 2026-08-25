# 离线安装说明

## 1. 准备

将完整 release 目录复制到监控中心和每个目标节点。用户只修改：

- `config/monitoring.yml` 中的 `public_host`
- 每个节点的 `address`
- GPU 类型和开关
- 外部推理服务 `/metrics` 端口

网络路径、SSH、ProxyJump、跳板机和凭据由用户环境自行提供，产品不处理。

## 2. 中心端

```bash
docker load -i images/inference-monitor-center-<version>.tar
python3 monitorctl.py --config config/monitoring.yml render
CENTER_IMAGE=inference-monitor-center:<version> ./deploy/run-center.sh
```

## 3. 节点端

```bash
docker load -i images/inference-monitor-node-musa-<version>.tar
NODE_ENV=$PWD/monitoring/generated/nodes/<节点name>.env \
NODE_IMAGE=inference-monitor-node-musa:<version> \
./deploy/run-node-musa.sh
```

每个需要采集节点指标的机器运行一个 node 容器；整个集群只运行一个 center 容器。

NVIDIA节点使用`inference-monitor-node-nvidia`和`deploy/run-node-nvidia.sh`。

## 4. 验证和地址

```bash
python3 monitorctl.py --config config/monitoring.yml status
python3 monitorctl.py --config config/monitoring.yml urls
```

最终地址会写入 `monitoring/generated/access.json`。
