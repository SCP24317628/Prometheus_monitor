# Inference Monitor 0.1.7

## 版本目标

0.1.7 增加 MoE 专家分布监控，面向开启 SGLang
`--enable-expert-distribution-metrics` 的推理服务。Center 仍为单容器，Node
仍按节点部署，DCGM 默认关闭。

## 新增能力

- Prometheus 继续原样抓取 SGLang `/metrics`，无需在 Node 中复制或改写 SGLang
  指标。
- 新增统一 MoE 面板：专家负载均衡趋势，以及按层和 GPU rank 的专家分布趋势。
- 新增 0.1.7 配置、镜像默认标签、离线打包和校验流程。
- 支持将 Center、MUSA Node、可选 nvidia-smi Node 和对应说明作为同一版本交付。

## SGLang 启动要求

在 SGLang 服务启动参数加入：

```text
--enable-metrics --enable-expert-distribution-metrics
```

当前检出的 SGLang 版本会将该开关解析为 `stat` recorder（若未显式设置
recorder mode）。`sglang:eplb_balancedness` 是 Summary，按 `forward_mode` 记录；
`sglang:eplb_gpu_physical_count` 是按 `layer` 的 Histogram，桶表示 GPU rank。
没有 MoE、没有开启该开关或 SGLang 版本未暴露这些序列时，Grafana 显示 No data
是正确结果。

## 版本对应关系

源码 Git tag、Center/Node 镜像 tag、离线包目录和 GitHub Release 必须全部使用
`0.1.7`。离线包 manifest 记录 Git commit、镜像 SHA256 和是否包含可选镜像。
