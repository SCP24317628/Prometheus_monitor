# Inference Monitor 离线发布包

这是面向最终用户的离线交付物。包内应包含：

```text
inference-monitor-offline-<VERSION>/
├── README.md / RELEASE_NOTES.md
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
    └── (0.1.6不包含NVIDIA/DCGM镜像)
```

用户不需要执行 `docker build`，只需 `docker load` 后按
`INSTALL_OFFLINE.md`进入`product/`，再按`product/INSTALL_QUICKSTART.md`启动
center和node。镜像、配置和源码版本必须一致。

发布者使用 `build-offline-package.ps1` 生成目录、tar、manifest和SHA256：

```powershell
.\release\build-offline-package.ps1 `
  -CenterImageTar <center-image.tar> `
  -MusaImageTar <node-musa-image.tar> `
  -NvidiaImageTar <node-nvidia-image.tar>   # 可选
```

0.1.6明确不包含NVIDIA/DCGM组件。NVIDIA/DCGM计划在后续版本单独交付；本包的
manifest会明确标记该组件延期，不把源码接口或Dockerfile表述成已交付镜像。
