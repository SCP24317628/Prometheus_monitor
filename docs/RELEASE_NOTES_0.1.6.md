# Inference Monitor 0.1.6 Release Notes

## 发布目标

0.1.6是面向跨环境迁移的可靠性和安全修复版本。正式离线包必须同时包含Center、
MUSA Node和基于官方DCGM Exporter的NVIDIA Node镜像。

## 已确认产品决策

- SSH、ProxyJump和跳板网络由用户负责；产品提供本机部署和Center视角验收。
- Center与Agent的监听地址由用户显式配置，禁止默认绑定`0.0.0.0`。
- 继续使用Prometheus+Grafana单Center容器，组件拆分推迟到0.2.0。
- NVIDIA镜像是完整0.1.6离线交付的必选项，不允许仅交付Dockerfile。

## 计划修复

- 修复Center的POSIX进程管理、Grafana homepath和子进程退出传播。
- 增加容器HEALTHCHECK并关闭Grafana匿名访问。
- 引入Schema V2、多网络地址、维护态、强配置门禁和统一部署入口。
- 增加自动预检、幂等升级、失败回滚和统一验收报告。
- 记录镜像ID、架构、SHA256、配置hash和离线Artifact来源。
