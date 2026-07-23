#Requires -Version 5.1
<#
.SYNOPSIS
  Background loop: invoke src proxy-guardian with live dead + broken clear.
.DESCRIPTION
  Started hidden by install-dead-proxy-guardian.ps1 Startup hook.
  Calls:
    python -m src proxy-guardian --once
      --confirm CLEAR_DEAD_LOCALHOST_PROXY
      --clear-broken --confirm-broken PREFER_DIRECT_WININET
      --dry-run false

  Clears HKCU WinINET when:
    - localhost proxy enabled and no listener (dead), or
    - listener up but proxy path fails while direct HTTPS works (broken)

  Does NOT clear a healthy active localhost proxy.
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
    $portable = Join-Path $RepoRoot '.tools\python312\python.exe'
    if (Test-Path -LiteralPath $portable) {
        $Python = $portable
    } else {
        $Python = (Get-Command python -ErrorAction Stop).Source
    }
}
Set-Location -LiteralPath $RepoRoot
$env:PYTHONPATH = $RepoRoot
$interval = [Math]::Max(15, $IntervalSeconds)

while ($true) {
    & $Python -m src proxy-guardian --once `
        --confirm CLEAR_DEAD_LOCALHOST_PROXY `
        --clear-broken `
        --confirm-broken PREFER_DIRECT_WININET `
        --dry-run false `
        --json | Out-Null
    Start-Sleep -Seconds $interval
}
