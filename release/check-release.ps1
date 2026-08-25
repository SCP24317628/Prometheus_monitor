[CmdletBinding()]
param([string]$Version = "0.1.4")
$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$required = @(
  "monitorctl.py", "requirements.txt", "config/monitoring.yml",
  "images/center/Dockerfile", "images/node-musa/Dockerfile",
  "deploy/run-center.sh", "deploy/run-node-musa.sh",
  "monitoring/grafana/dashboards/inference-overview.json",
  "monitoring/grafana/dashboards/sglang-detailed.json"
)
$missing = @($required | Where-Object { -not (Test-Path (Join-Path $root $_)) })
$imageTars = @(
  (Join-Path $root "images/inference-monitor-center-$Version.tar"),
  (Join-Path $root "images/inference-monitor-node-musa-$Version.tar")
)
Write-Host "Source checks:"
if ($missing.Count) { $missing | ForEach-Object { Write-Host "MISSING $_" } } else { Write-Host "OK source files" }
Write-Host "Image checks:"
foreach ($tar in $imageTars) {
  if (Test-Path $tar) { Write-Host "OK $tar" } else { Write-Host "MISSING $tar" }
}
if ($missing.Count -or @($imageTars | Where-Object { -not (Test-Path $_) }).Count) { exit 2 }
Write-Host "RELEASE_READY"
