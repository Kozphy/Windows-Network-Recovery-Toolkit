#Requires -Version 5.1
<#
.SYNOPSIS
  Preview or install startup observability (guardian + boot trace).
#>
param(
    [int]$GuardianIntervalSeconds = 60,
    [int]$BootTraceDurationSeconds = 180,
    [int]$BootTraceIntervalSeconds = 2,
    [switch]$Uninstall,
    [switch]$Apply
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Python)) {
    $Python = (Get-Command python -ErrorAction Stop).Source
}

Set-Location -LiteralPath $RepoRoot
$env:PYTHONPATH = $RepoRoot

if ($Uninstall) {
    if ($Apply) {
        & $Python -m src uninstall-startup-observability `
            --confirm UNINSTALL_STARTUP_OBSERVABILITY `
            --dry-run false
    } else {
        & $Python -m src uninstall-startup-observability
    }
    exit $LASTEXITCODE
}

if ($Apply) {
    & $Python -m src install-startup-observability `
        --guardian-interval $GuardianIntervalSeconds `
        --duration $BootTraceDurationSeconds `
        --interval $BootTraceIntervalSeconds `
        --confirm INSTALL_STARTUP_OBSERVABILITY `
        --dry-run false
} else {
    & $Python -m src install-startup-observability `
        --guardian-interval $GuardianIntervalSeconds `
        --duration $BootTraceDurationSeconds `
        --interval $BootTraceIntervalSeconds
}
exit $LASTEXITCODE
