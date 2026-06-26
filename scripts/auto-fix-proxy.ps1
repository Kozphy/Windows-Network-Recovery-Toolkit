#Requires -Version 5.1
<#
.SYNOPSIS
  One-shot automatic fix for dead localhost WinINET proxy (no prompts).
.DESCRIPTION
  1. Disables Cursor system-proxy management (root cause)
  2. Runs proxy-guardian live apply when DEAD_PROXY_CONFIG is detected
  3. Ensures background guardian is installed (1-minute loop)
  4. Prints final proxy-status classification

  Safe: guardian only clears proxy when enabled localhost port has NO listener.
.NOTES
  No admin required. HKCU WinINET only.
#>
param(
    [switch]$SkipGuardianInstall
)

$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Python = Join-Path $RepoRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $Python)) {
    $Python = (Get-Command python -ErrorAction Stop).Source
}

Set-Location -LiteralPath $RepoRoot
$env:PYTHONPATH = $RepoRoot

Write-Host "=== Auto-fix dead proxy ===" -ForegroundColor Cyan

& (Join-Path $PSScriptRoot 'configure-cursor-no-proxy.ps1')

Write-Host ""
Write-Host "Running proxy-guardian (live apply if dead proxy detected)..." -ForegroundColor Cyan
$guardianJson = & $Python -m windows_network_toolkit proxy-guardian --once 2>&1 | Out-String
Write-Host $guardianJson

if (-not $SkipGuardianInstall) {
    Write-Host ""
    Write-Host "Ensuring background guardian (1-minute checks)..." -ForegroundColor Cyan
    & (Join-Path $PSScriptRoot 'install-dead-proxy-guardian.ps1') -IntervalMinutes 1
}

Write-Host ""
Write-Host "Current status:" -ForegroundColor Cyan
$statusJson = & $Python -m windows_network_toolkit proxy-status 2>&1 | Out-String
Write-Host $statusJson

if ($statusJson -match '"classification":\s*"NO_PROXY"') {
    Write-Host "OK: Proxy path is clean. Restart your browser." -ForegroundColor Green
    exit 0
}
if ($statusJson -match '"classification":\s*"DEAD_PROXY_CONFIG"') {
    Write-Host "WARN: Still DEAD_PROXY_CONFIG — try fix-wininet-proxy.cmd manually." -ForegroundColor Yellow
    exit 1
}
Write-Host "Review proxy-status output above." -ForegroundColor Yellow
exit 0
