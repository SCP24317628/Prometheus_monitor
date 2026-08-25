# Inference Monitor Release Package

这是给最终用户的离线发布包结构。正式离线包应包含：

```text
inference-monitor-<version>/
├── monitorctl.py
├── requirements.txt
├── config/monitoring.yml
├── monitoring/
├── deploy/
├── images/
│   ├── inference-monitor-center-<version>.tar
│   ├── inference-monitor-node-musa-<version>.tar
│   └── inference-monitor-node-nvidia-<version>.tar（可选）
└── INSTALL_OFFLINE.md
```

`images/*.tar` 是发布门槛：最终用户不需要 Docker build，只执行
`docker load` 后运行两个容器。

发布前运行 `release/check-release.ps1`，确认源码、必需镜像tar和校验文件齐全。
