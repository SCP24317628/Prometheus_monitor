[CmdletBinding()]
param([string]$Config = "config/monitoring-only.example.yml")
$ErrorActionPreference = "Stop"
python monitorctl.py --config $Config status
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
