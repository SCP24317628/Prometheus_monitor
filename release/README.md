# Inference Monitor 离线发布包

这是面向最终用户的离线交付物。包内应包含：

```text
inference-monitor-<VERSION>/
├── INSTALL_QUICKSTART.md
├── monitorctl.py / requirements.txt
├── config/monitoring.yml
├── monitoring/ / deploy/
└── images/
    ├── inference-monitor-center-<VERSION>.tar
    ├── inference-monitor-node-musa-<VERSION>.tar
    └── inference-monitor-node-nvidia-<VERSION>.tar（可选）
```

用户不需要执行 `docker build`，只需 `docker load` 后按
`INSTALL_QUICKSTART.md` 启动 center 和 node。镜像、配置和源码版本必须一致。
