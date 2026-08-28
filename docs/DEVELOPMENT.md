# 开发与发布文档

本文面向产品开发者和发布人员，不面向最终使用者。

## 构建镜像

```bash
REGISTRY=local TAG=0.1.5 ./deploy/build-images.sh
```

构建结果：

```text
registry.example.com/monitoring/inference-monitor-center:0.1.5
registry.example.com/monitoring/inference-monitor-node-musa:0.1.5
```

## 推送镜像

```bash
docker push registry.example.com/monitoring/inference-monitor-center:0.1.5
docker push registry.example.com/monitoring/inference-monitor-node-musa:0.1.5
```

发布说明必须给最终用户真实 registry 或离线 tar 和不可变版本，不能要求最终用户执行 `docker build`。

离线构建前，准备已校验的官方 tarball：

```text
images/center/prometheus.tar.gz
images/center/grafana.tar.gz
```

`Dockerfile.slim` 使用通用 Ubuntu 基础层；`node-musa/Dockerfile` 使用通用 Ubuntu + MUSA runtime 注入的最小 node 镜像，不得回退到完整 SGLang 镜像。

内网镜像代理可通过构建参数覆盖，不应修改Dockerfile：

```bash
MUSA_BASE_IMAGE=registry.example.com/mirror/ubuntu:22.04 ./deploy/build-images.sh
```

## 验证

```bash
python monitorctl.py --config config/monitoring.yml render
python monitorctl.py --config config/monitoring.yml urls
python -m unittest discover -s tests -v
```

发布前还要验证：

- 两个 Dockerfile 构建成功。
- center 同时提供 Prometheus `/-/ready` 和 Grafana `/api/health`。
- node 同时提供 `:9100/metrics` 和 `:9500/metrics`。
- Prometheus 所有配置的 targets 为 UP；SGLang worker targets 只有在对应服务运行
  且 `/metrics` 可访问时才应为 UP。
- 统一 Overview Dashboard 已 provisioning；SGLang 详细面板作为同一张看板的下方区块加载。
- Prefill/Decode 的 SGLang PromQL 通过真实 Prometheus 验证；Router 不属于默认 target。

## 高级入口

- `images/center/`：中心一体化镜像。
- `images/node-musa/`：MUSA 节点一体化镜像。
- `deploy/build-images.sh`：发布构建入口。
- `monitoring/docker-compose.*.yml`：开发、调试和拆分组件部署。
- `deploy/dsv4/`：测试环境样例，不属于产品发布物。

## 正式离线发布

1. 更新`VERSION`和所有默认镜像标签。
2. 构建并保存center、node-musa，以及需要交付的node-nvidia镜像。
3. 使用`release/build-offline-package.ps1`生成离线包。
4. 使用`release/check-release.ps1`验证源码、配置、测试、manifest和包结构。
5. 核对`SHA256SUMS`及外层tar的`.sha256`后再创建Git tag。

```powershell
.\release\build-offline-package.ps1 `
  -CenterImageTar <center-image.tar> `
  -MusaImageTar <node-musa-image.tar> `
  -NvidiaImageTar <node-nvidia-image.tar>
```

```bash
git tag v0.1.5
git push origin v0.1.5
```
