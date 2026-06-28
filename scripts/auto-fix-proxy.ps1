#Requires -Version 5.1
<#
.SYNOPSIS
  One-shot automatic fix for dead localhost WinINET proxy (no prompts).
.DESCRIPTION
  Orchestrates the dead-proxy recovery layer documented in docs/dead-proxy-guardian.md.

  Steps:
    1. configure-cursor-no-proxy.ps1 — stop Cursor from re-enabling system proxy
    2. proxy-guardian --once — live apply when classification is DEAD_PROXY_CONFIG
    3. install-dead-proxy-guardian.ps1 — optional 1-minute background loop (default)
    4. proxy-status — print final classification JSON

  Inputs:
    -SkipGuardianInstall  Skip step 3 (guardian install / background loop)

  Outputs:
    JSON from proxy-guardian and proxy-status on stdout; exit 0/1 from classification

  Privileges:
    No administrator required. Mutates HKCU WinINET only via proxy-guardian when safe.

  Side effects:
    - Cursor User/settings.json (http.proxySupport=off)
    - HKCU WinINET registry when DEAD_PROXY_CONFIG and no localhost listener
    - Startup hook WNRT-DeadProxyGuardian.cmd unless -SkipGuardianInstall
    - May append .audit/proxy-disable.jsonl on guardian apply

  Safety boundaries:
    Guardian never clears proxy while a process listens on the configured localhost port.
    Does not disable corporate VPN or mandatory enterprise proxy by design.

  Idempotency:
    Safe to rerun. Guardian apply is no-op when classification is not DEAD_PROXY_CONFIG.

  Recovery:
    If still DEAD_PROXY_CONFIG, run scripts/fix-wininet-proxy.cmd or preview:
      python -m windows_network_toolkit proxy-disable --dry-run

  Example:
    .\scripts\auto-fix-proxy.ps1
    .\scripts\auto-fix-proxy.ps1 -SkipGuardianInstall
.NOTES
  Audit: review proxy-status JSON and .audit/proxy-disable.jsonl after apply.
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
