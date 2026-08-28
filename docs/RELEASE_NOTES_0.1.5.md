# Inference Monitor 0.1.5 Release Notes

## 交付范围

- 一个center容器：Prometheus + Grafana。
- 每个MUSA节点一个node容器：node_exporter + MUSA exporter。
- NVIDIA node的Dockerfile、启动脚本和插件接口；离线包是否捆绑NVIDIA镜像以
  `release-manifest.json`为准。
- 可迁移配置模板、渲染工具、PRD、指标目录和离线安装手册。

## 本版本主要变化

- Router不再是默认监控target；Prefill/Decode端口和角色由用户显式配置。
- 支持多个Prefill和Decode worker，所有诊断曲线保留`node`和`role`。
- 并发、排队、Token吞吐、TTFT、E2E全部改为时间序列，不再依赖瞬时数字卡片。
- Token吞吐单位明确为`tok/s`，不伪装为TOPS/TFLOPS。
- CPU使用率显示0–100%，内存自动显示GiB/TiB。
- 推测解码拆分为Draft/Accepted Length与Acceptance Rate两张图。
- Prefill/Decode关键阶段p95分开展示；新增默认折叠的Prefill二级诊断区。
- RDMA优先于Ethernet展示；没有链路容量telemetry时不伪造占用率。
- MUSA MTDCGM和NVIDIA DCGM保持默认关闭，由配置显式开启。
- 新增完整指标目录、正式安装手册、动态版本校验和离线打包器。

## 已知边界

- 产品抓取SGLang `/metrics`，不启动推理服务，不解析SGLang日志。
- 当前运行版本未暴露可用的ITL/TPOT histogram和Decode Forward histogram，
  看板不会用其他指标伪造。
- 静态target在IP、端口和路径不变时会在SGLang重启后自动恢复；端口或角色变化
  必须重新渲染center配置。
- 自动端口发现不属于V1默认行为。

## 发布验证

发布包必须通过：

```powershell
.\release\check-release.ps1 -Version 0.1.5 -PackageDir <解压目录>
```

并保留`release-manifest.json`、包内`SHA256SUMS`和外层tar的`.sha256`文件。
