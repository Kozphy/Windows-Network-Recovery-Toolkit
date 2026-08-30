# Short proxy-watch soak: detect WinINET rewrite after clear / during reproduction.
# Read-only. Exit 1 when ProxyEnable flips 0→1 (REWRITE_DETECTED).
#
# Usage:
#   .\scripts\proxy-watch-soak.ps1
#   .\scripts\proxy-watch-soak.ps1 -Minutes 3 -Interval 2
#   .\scripts\proxy-watch-soak.ps1 -NoExitOnRewrite

param(
    [double]$Minutes = 2.0,
    [double]$Interval = 3.0,
    [switch]$NoExitOnRewrite,
    [string]$EvidenceCsv = ""
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root
$env:PYTHONPATH = $root

$argsList = @(
    "-m", "src", "proxy-watch",
    "--interval", "$Interval",
    "--soak-minutes", "$Minutes"
)
if ($NoExitOnRewrite) {
    $argsList += "--no-exit-on-rewrite"
}
if ($EvidenceCsv) {
    $argsList += @("--evidence-csv", $EvidenceCsv)
}

Write-Host "proxy-watch soak: ${Minutes}m @ ${Interval}s (read-only; pair with Procmon filter set for writer proof)"
python @argsList
exit $LASTEXITCODE
