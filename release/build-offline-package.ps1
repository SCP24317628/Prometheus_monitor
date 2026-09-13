param(
    [string]$Version = "",
    [Parameter(Mandatory = $true)][string]$CenterImageTar,
    [Parameter(Mandatory = $true)][string]$MusaImageTar,
    [string]$OutputRoot = ""
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
if (-not $Version) { $Version = (Get-Content -LiteralPath (Join-Path $repoRoot "VERSION") -Raw).Trim() }
if (-not $OutputRoot) { $OutputRoot = $PSScriptRoot }

$center = (Resolve-Path -LiteralPath $CenterImageTar).Path
$musa = (Resolve-Path -LiteralPath $MusaImageTar).Path
$packageName = "inference-monitor-offline-$Version"
$packageDir = Join-Path $OutputRoot $packageName
$archive = Join-Path $OutputRoot "$packageName.tar"
$archiveGzip = Join-Path $OutputRoot "$packageName.tar.gz"

function Compress-GzipFile {
    param([Parameter(Mandatory = $true)][string]$InputPath, [Parameter(Mandatory = $true)][string]$OutputPath)
    $inputStream = [IO.File]::OpenRead($InputPath)
    try {
        $outputStream = [IO.File]::Create($OutputPath)
        try {
            $gzip = New-Object IO.Compression.GZipStream($outputStream, [IO.Compression.CompressionMode]::Compress)
            try { $inputStream.CopyTo($gzip) } finally { $gzip.Dispose() }
        } finally { $outputStream.Dispose() }
    } finally { $inputStream.Dispose() }
}

if (Test-Path -LiteralPath $packageDir) { Remove-Item -LiteralPath $packageDir -Recurse -Force }
if (Test-Path -LiteralPath $archive) { Remove-Item -LiteralPath $archive -Force }
if (Test-Path -LiteralPath $archiveGzip) { Remove-Item -LiteralPath $archiveGzip -Force }
if (Test-Path -LiteralPath "$archive.sha256") { Remove-Item -LiteralPath "$archive.sha256" -Force }
if (Test-Path -LiteralPath "$archiveGzip.sha256") { Remove-Item -LiteralPath "$archiveGzip.sha256" -Force }
New-Item -ItemType Directory -Path (Join-Path $packageDir "images") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $packageDir "source") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $packageDir "product") -Force | Out-Null

Copy-Item -LiteralPath (Join-Path $repoRoot "VERSION") -Destination $packageDir
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "README.md") -Destination $packageDir
Copy-Item -LiteralPath (Join-Path $PSScriptRoot "INSTALL_OFFLINE.md") -Destination $packageDir
$releaseNotes = Join-Path $repoRoot "docs/RELEASE_NOTES_$Version.md"
if (-not (Test-Path -LiteralPath $releaseNotes)) { throw "Missing release notes: $releaseNotes" }
Copy-Item -LiteralPath $releaseNotes -Destination (Join-Path $packageDir "RELEASE_NOTES.md")
Copy-Item -LiteralPath $center -Destination (Join-Path $packageDir "images/inference-monitor-center-$Version.tar")
Copy-Item -LiteralPath $musa -Destination (Join-Path $packageDir "images/inference-monitor-node-musa-$Version.tar")
$centerPackageTar = Join-Path $packageDir "images/inference-monitor-center-$Version.tar"
$musaPackageTar = Join-Path $packageDir "images/inference-monitor-node-musa-$Version.tar"
$centerPackageGzip = "$centerPackageTar.gz"
$musaPackageGzip = "$musaPackageTar.gz"
Compress-GzipFile -InputPath $centerPackageTar -OutputPath $centerPackageGzip
Compress-GzipFile -InputPath $musaPackageTar -OutputPath $musaPackageGzip
Remove-Item -LiteralPath $centerPackageTar, $musaPackageTar -Force

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
    # 0.1.6 intentionally ships no DCGM/NVIDIA component. Keep those interfaces
    # in Git for the later release, but remove them from this product directory.
    $excluded = @(
        "product/exporters/mtdcgm_exporter.py",
        "product/plugins/musa_dcgm",
        "product/plugins/nvidia_dcgm",
        "product/images/node-nvidia",
        "product/deploy/run-node-nvidia.sh"
    )
    foreach ($relative in $excluded) {
        $path = Join-Path $packageDir $relative
        if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path -Recurse -Force }
    }
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
    image_artifacts = @(
        [ordered]@{
            image = "inference-monitor-center:$Version"
            file = "images/inference-monitor-center-$Version.tar.gz"
            sha256 = (Get-FileHash -LiteralPath $centerPackageGzip -Algorithm SHA256).Hash.ToLowerInvariant()
            compression = "gzip"
            provenance = "release image artifact supplied to the offline packager and verified by SHA256"
        },
        [ordered]@{
            image = "inference-monitor-node-musa:$Version"
            file = "images/inference-monitor-node-musa-$Version.tar.gz"
            sha256 = (Get-FileHash -LiteralPath $musaPackageGzip -Algorithm SHA256).Hash.ToLowerInvariant()
            compression = "gzip"
            provenance = "release image artifact supplied to the offline packager and verified by SHA256"
        }
    )
    nvidia_image_bundled = $false
    nvidia_delivery_note = "NVIDIA/DCGM is intentionally not part of 0.1.6; reserved for a later release"
    credentials_included = $false
    runtime_data_included = $false
}
$manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $packageDir "release-manifest.json") -Encoding utf8

$sumFile = Join-Path $packageDir "SHA256SUMS"
$lines = Get-ChildItem -LiteralPath $packageDir -Recurse -File |
    Where-Object { $_.FullName -ne $sumFile } |
    Sort-Object FullName |
    ForEach-Object {
        $relative = $_.FullName.Substring($packageDir.Length).TrimStart('\', '/').Replace("\", "/")
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
Compress-GzipFile -InputPath $archive -OutputPath $archiveGzip
$archiveHash = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant()
"$archiveHash  $packageName.tar" | Set-Content -LiteralPath "$archive.sha256" -Encoding ascii
$archiveGzipHash = (Get-FileHash -LiteralPath $archiveGzip -Algorithm SHA256).Hash.ToLowerInvariant()
"$archiveGzipHash  $packageName.tar.gz" | Set-Content -LiteralPath "$archiveGzip.sha256" -Encoding ascii
Write-Host "Offline package: $archive"
Write-Host "SHA256: $archiveHash"
Write-Host "Compressed offline package: $archiveGzip"
Write-Host "Compressed SHA256: $archiveGzipHash"
