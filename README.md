# Prometheus + Grafana 推理监控产品

最终用户请直接阅读：[INSTALL_QUICKSTART.md](INSTALL_QUICKSTART.md)

指标名称、来源、端口和当前环境状态见：[指标目录](docs/METRICS_CATALOG.md)

本产品提供一个中心容器和每节点一个采集容器：

```text
center：Prometheus + Grafana
node：node_exporter + MUSA/NVIDIA GPU exporter
```

产品只抓取 Prometheus-compatible `/metrics`，不启动或管理推理服务，不解析
SGLang 日志，也不实现 SSH、ProxyJump、跳板机、VPN 或端口转发。

核心接入对象是 SGLang Prefill/Decode worker；Router 监控不是默认链路。用户在
`config/monitoring.local.yml` 中手动登记实际 metrics 端口和 `prefill`/`decode`
角色，中心 Prometheus 再汇总所有节点数据。

MUSA MTDCGM 和 NVIDIA DCGM 默认关闭，只有在配置中显式启用并满足宿主机依赖时
才会启动。

开发、镜像构建和版本发布说明见：[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)
