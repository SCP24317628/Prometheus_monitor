param(
    [string]$Version = "",
    [string]$PackageDir = ""
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$validatePackage = [bool]$PackageDir
if (-not $Version) {
    $Version = (Get-Content -LiteralPath (Join-Path $repoRoot "VERSION") -Raw).Trim()
}

$requiredSource = @(
    "VERSION", "README.md", "INSTALL_QUICKSTART.md", "config/monitoring.yml",
    "deploy/run-center.sh", "deploy/run-node-musa.sh", "deploy/run-node-nvidia.sh",
    "monitoring/grafana/dashboards/inference-overview.json",
    "docs/PRD_V1.md", "docs/METRICS_CATALOG.md"
)
foreach ($relative in $requiredSource) {
    if (-not (Test-Path -LiteralPath (Join-Path $repoRoot $relative))) {
        throw "Missing source delivery file: $relative"
    }
}

$versionReferences = @(
    "deploy/run-center.sh", "deploy/run-node-musa.sh", "deploy/run-node-nvidia.sh",
    "monitoring/docker-compose.center.yml", "monitoring/docker-compose.node.yml"
)
foreach ($relative in $versionReferences) {
    $text = Get-Content -LiteralPath (Join-Path $repoRoot $relative) -Raw
    if ($text -notmatch [regex]::Escape($Version)) {
        throw "$relative does not reference release version $Version"
    }
}

Push-Location $repoRoot
try {
    python -m unittest discover -s tests -p "test_*.py"
    if ($LASTEXITCODE -ne 0) { throw "Unit tests failed" }
    python tools/render_config.py config/monitoring.yml --output "$env:TEMP/inference-monitor-prometheus-$Version.yml" --env-output "$env:TEMP/inference-monitor-env-$Version"
    if ($LASTEXITCODE -ne 0) { throw "Config rendering failed" }
    git diff --check
    if ($LASTEXITCODE -ne 0) { throw "git diff --check failed" }
} finally {
    Pop-Location
}

if ($validatePackage) {
    if (-not (Test-Path -LiteralPath $PackageDir)) { throw "Package directory not found: $PackageDir" }
    $requiredPackage = @(
        "VERSION", "INSTALL_QUICKSTART.md", "INSTALL_OFFLINE.md",
        "release-manifest.json", "SHA256SUMS",
        "source/inference-monitor-source-$Version.zip",
        "product/monitorctl.py", "product/config/monitoring.yml",
        "product/deploy/run-center.sh", "product/deploy/run-node-musa.sh",
        "images/inference-monitor-center-$Version.tar",
        "images/inference-monitor-node-musa-$Version.tar"
    )
    foreach ($relative in $requiredPackage) {
        if (-not (Test-Path -LiteralPath (Join-Path $PackageDir $relative))) {
            throw "Missing package artifact: $relative"
        }
    }
    $manifest = Get-Content -LiteralPath (Join-Path $PackageDir "release-manifest.json") -Raw | ConvertFrom-Json
    if ($manifest.version -ne $Version) { throw "Manifest version mismatch" }
    if ($manifest.default_dcgm_enabled -ne $false) { throw "DCGM must be disabled by default" }
}

Write-Host "Release validation passed: $Version"
