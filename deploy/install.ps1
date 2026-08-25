[CmdletBinding()]
param([string]$Config = "config/monitoring-only.example.yml", [switch]$Center, [switch]$Node)
$ErrorActionPreference = "Stop"
python monitorctl.py --config $Config render
if (-not $Center -and -not $Node) { throw "Use -Center and/or -Node" }
if ($Center) { python monitorctl.py --config $Config install --center }
if ($Node) { python monitorctl.py --config $Config install --node }
python monitorctl.py --config $Config urls
