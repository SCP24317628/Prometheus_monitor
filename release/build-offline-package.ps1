param(
    [string]$Version = "",
    [Parameter(Mandatory = $true)][string]$CenterImageTar,
    [Parameter(Mandatory = $true)][string]$MusaImageTar,
    [string]$NvidiaImageTar = "",
    [string]$OutputRoot = ""
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
if (-not $Version) { $Version = (Get-Content -LiteralPath (Join-Path $repoRoot "VERSION") -Raw).Trim() }
if (-not $OutputRoot) { $OutputRoot = $PSScriptRoot }

$center = (Resolve-Path -LiteralPath $CenterImageTar).Path
$musa = (Resolve-Path -LiteralPath $MusaImageTar).Path
$nvidia = if ($NvidiaImageTar) { (Resolve-Path -LiteralPath $NvidiaImageTar).Path } else { $null }
$packageName = "inference-monitor-offline-$Version"
$packageDir = Join-Path $OutputRoot $packageName
$archive = Join-Path $OutputRoot "$packageName.tar"

if (Test-Path -LiteralPath $packageDir) { Remove-Item -LiteralPath $packageDir -Recurse -Force }
if (Test-Path -LiteralPath $archive) { Remove-Item -LiteralPath $archive -Force }
New-Item -ItemType Directory -Path (Join-Path $packageDir "images") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $packageDir "source") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $packageDir "product") -Force | Out-Null

Copy-Item -LiteralPath (Join-Path $repoRoot "VERSION") -Destination $packageDir
Copy-Item -LiteralPath (Join-Path $repoRoot "README.md") -Destination $packageDir
Copy-Item -LiteralPath (Join-Path $repoRoot "INSTALL_QUICKSTART.md") -Destination $packageDir
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "INSTALL_OFFLINE.md") -Destination $packageDir
Copy-Item -LiteralPath $center -Destination (Join-Path $packageDir "images/inference-monitor-center-$Version.tar")
Copy-Item -LiteralPath $musa -Destination (Join-Path $packageDir "images/inference-monitor-node-musa-$Version.tar")
if ($nvidia) {
    Copy-Item -LiteralPath $nvidia -Destination (Join-Path $packageDir "images/inference-monitor-node-nvidia-$Version.tar")
}

$sourceZip = Join-Path $packageDir "source/inference-monitor-source-$Version.zip"
$sourceTar = Join-Path $env:TEMP "inference-monitor-source-$Version.tar"
Push-Location $repoRoot
try {
    git archive --format=zip --output="$sourceZip" HEAD
    if ($LASTEXITCODE -ne 0) { throw "git archive failed" }
    git archive --format=tar --output="$sourceTar" HEAD
    if ($LASTEXITCODE -ne 0) { throw "git archive tar failed" }
    tar -xf "$sourceTar" -C (Join-Path $packageDir "product")
    if ($LASTEXITCODE -ne 0) { throw "source extraction failed" }
    $commit = (git rev-parse HEAD).Trim()
} finally {
    Pop-Location
    Remove-Item -LiteralPath $sourceTar -Force -ErrorAction SilentlyContinue
}

$manifest = [ordered]@{
    product = "Inference Monitor"
    version = $Version
    git_commit = $commit
    built_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    default_dcgm_enabled = $false
    default_router_monitoring = $false
    topology = "one center container plus one node container per monitored host"
    bundled_images = @("inference-monitor-center:$Version", "inference-monitor-node-musa:$Version")
    nvidia_image_bundled = [bool]$nvidia
    nvidia_delivery_note = if ($nvidia) { "bundled" } else { "Dockerfile and run script are included in source; build separately for the target NVIDIA environment" }
    credentials_included = $false
    runtime_data_included = $false
}
if ($nvidia) { $manifest.bundled_images += "inference-monitor-node-nvidia:$Version" }
$manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $packageDir "release-manifest.json") -Encoding utf8

$sumFile = Join-Path $packageDir "SHA256SUMS"
$lines = Get-ChildItem -LiteralPath $packageDir -Recurse -File |
    Where-Object { $_.FullName -ne $sumFile } |
    Sort-Object FullName |
    ForEach-Object {
        $relative = [IO.Path]::GetRelativePath($packageDir, $_.FullName).Replace("\", "/")
        "{0}  {1}" -f (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant(), $relative
    }
$lines | Set-Content -LiteralPath $sumFile -Encoding ascii

& (Join-Path $PSScriptRoot "check-release.ps1") -Version $Version -PackageDir $packageDir
if ($LASTEXITCODE -ne 0) { throw "Release validation failed" }

Push-Location $OutputRoot
try {
    tar -cf "$packageName.tar" "$packageName"
    if ($LASTEXITCODE -ne 0) { throw "tar creation failed" }
} finally {
    Pop-Location
}
$archiveHash = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant()
"$archiveHash  $packageName.tar" | Set-Content -LiteralPath "$archive.sha256" -Encoding ascii
Write-Host "Offline package: $archive"
Write-Host "SHA256: $archiveHash"
