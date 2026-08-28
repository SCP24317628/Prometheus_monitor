# Inference Monitor 离线发布包

这是面向最终用户的离线交付物。包内应包含：

```text
inference-monitor-offline-<VERSION>/
├── INSTALL_QUICKSTART.md
├── INSTALL_OFFLINE.md
├── release-manifest.json / SHA256SUMS
├── product/
│   ├── monitorctl.py / requirements.txt
│   ├── config/monitoring.yml
│   └── monitoring/ / deploy/
├── source/inference-monitor-source-<VERSION>.zip
└── images/
    ├── inference-monitor-center-<VERSION>.tar
    ├── inference-monitor-node-musa-<VERSION>.tar
    └── inference-monitor-node-nvidia-<VERSION>.tar（可选）
```

用户不需要执行 `docker build`，只需 `docker load` 后按
`INSTALL_QUICKSTART.md` 启动 center 和 node。镜像、配置和源码版本必须一致。

发布者使用 `build-offline-package.ps1` 生成目录、tar、manifest和SHA256：

```powershell
.\release\build-offline-package.ps1 `
  -CenterImageTar <center-image.tar> `
  -MusaImageTar <node-musa-image.tar> `
  -NvidiaImageTar <node-nvidia-image.tar>   # 可选
```

正式包最低包含center和MUSA node镜像。NVIDIA镜像未传入时，manifest会明确标记
未捆绑；源码包仍包含NVIDIA Dockerfile和启动脚本，不能把“可构建”表述成“已交付镜像”。
