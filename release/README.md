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
    ├── inference-monitor-center-<VERSION>.tar.gz
    ├── inference-monitor-node-musa-<VERSION>.tar.gz
    └── inference-monitor-node-nvidia-<VERSION>.tar.gz（可选，nvidia-smi，无DCGM）
```

用户不需要执行 `docker build`，只需 `docker load` 后按
`INSTALL_OFFLINE.md`进入`product/`，再按`product/INSTALL_QUICKSTART.md`启动
center和node。镜像、配置和源码版本必须一致。

发布者使用 `build-offline-package.ps1` 生成目录、`.tar`/`.tar.gz`、manifest和SHA256：

```powershell
.\release\build-offline-package.ps1 `
  -CenterImageTar <center-image.tar> `
  -MusaImageTar <node-musa-image.tar>
  -NvidiaSmiImageTar <node-nvidia-smi-image.tar>
```

最终用户优先加载 `.tar.gz`；Docker 会直接解压并导入，若环境不支持则加载同名
`.tar`。外层离线包也同时提供 `inference-monitor-offline-<VERSION>.tar.gz`。

0.1.6明确不包含NVIDIA/DCGM组件。该版本的`product/`目录也不包含DCGM/NVIDIA
插件和镜像构建文件；NVIDIA/DCGM计划在后续版本单独交付。完整源码仓库仍保留
后续版本开发所需的接口，但不属于本次离线交付物。
