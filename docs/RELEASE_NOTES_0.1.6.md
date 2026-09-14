# Inference Monitor 0.1.6 Release Notes

## 发布目标

0.1.6是面向跨环境迁移的可靠性和安全修复版本。正式离线包包含Center和无DCGM的
MUSA Node；NVIDIA/DCGM组件延期到后续版本。

## 已确认产品决策

- SSH、ProxyJump和跳板网络由用户负责；产品提供本机部署和Center视角验收。
- Center与Agent的监听地址由用户显式配置，禁止默认绑定`0.0.0.0`。
- 继续使用Prometheus+Grafana单Center容器，组件拆分推迟到0.2.0。
- NVIDIA/DCGM不属于0.1.6交付范围，后续版本单独验收和交付。

## 计划修复

- 修复Center的POSIX进程管理、Grafana homepath和子进程退出传播。
- 增加容器HEALTHCHECK并关闭Grafana匿名访问。
- 引入Schema V2、多网络地址、维护态、强配置门禁和统一部署入口。
- 增加自动预检、幂等升级、失败回滚和统一验收报告。
- 记录镜像ID、架构、SHA256、配置hash和离线Artifact来源。

## 交付体积处理

- Center 保持单容器，并基于已验证的运行时内容做层扁平化，减少重复基础层；77 上
  烟雾验证 Prometheus `/-/ready` 和 Grafana `/api/health` 均通过。
- 离线包内镜像采用 `docker save` 的 gzip 压缩格式，用户直接执行
  `docker load -i *.tar.gz`；外层包同时提供 `.tar` 和 `.tar.gz` 校验文件。
- 0.1.6 离线包携带压缩后的 Center、无 DCGM 的 MUSA Node，以及可选的无 DCGM
  NVIDIA Node（基于宿主机 `nvidia-smi`），避免同一镜像的 `.tar`/`.tar.gz`
  重复占用交付体积。
