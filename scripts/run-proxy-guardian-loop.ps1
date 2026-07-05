#Requires -Version 5.1
<#
.SYNOPSIS
  Background loop: invoke src proxy-guardian with live dead-proxy clear on an interval.
.DESCRIPTION
  Started hidden by install-dead-proxy-guardian.ps1 Startup hook.
  Calls: python -m src proxy-guardian --once --confirm CLEAR_DEAD_LOCALHOST_PROXY --dry-run false

  Inputs:
    -IntervalSeconds  Sleep between checks (default 60)

  Safety:
    Clears HKCU WinINET only when localhost proxy is enabled and no listener is bound.
.NOTES
  Do not run multiple instances — install script stops existing loop before StartNow.
#>
param(
    [int]$IntervalSeconds = 60
)

$ErrorActionPreference = 'SilentlyContinue'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Python = Join-Path $RepoRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $Python)) {
    $Python = (Get-Command python -ErrorAction Stop).Source
}
Set-Location -LiteralPath $RepoRoot
$env:PYTHONPATH = $RepoRoot
$interval = [Math]::Max(15, $IntervalSeconds)

while ($true) {
    & $Python -m src proxy-guardian --once `
        --confirm CLEAR_DEAD_LOCALHOST_PROXY `
        --dry-run false `
        --json | Out-Null
    Start-Sleep -Seconds $interval
}
