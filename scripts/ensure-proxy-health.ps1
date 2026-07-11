#Requires -Version 5.1
<#
.SYNOPSIS
  Ensure WinINET proxy health when opening / running this repo.
.DESCRIPTION
  Clears dead localhost proxies, installs startup observability if missing,
  and optionally forces direct access (--PreferDirect) for LinkedIn/browser reliability.

  Examples:
    .\scripts\ensure-proxy-health.ps1
    .\scripts\ensure-proxy-health.ps1 -PreferDirect
    .\scripts\ensure-proxy-health.ps1 -DryRun
#>
param(
    [switch]$PreferDirect,
    [switch]$DryRun,
    [switch]$SkipObservabilityInstall,
    [switch]$SkipCursorFix,
    [int]$IntervalSeconds = 60
)

$ErrorActionPreference = 'Continue'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Python = Join-Path $RepoRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $Python)) {
    $Python = (Get-Command python -ErrorAction Stop).Source
}

Set-Location -LiteralPath $RepoRoot
$env:PYTHONPATH = $RepoRoot

Write-Host "=== Ensure proxy health (WNRT) ===" -ForegroundColor Cyan

$argsList = @(
    '-m', 'src', 'ensure-proxy-health',
    '--json',
    '--guardian-interval', "$IntervalSeconds"
)
if ($DryRun) { $argsList += '--dry-run' }
if ($SkipObservabilityInstall) { $argsList += '--skip-observability-install' }
if ($SkipCursorFix) { $argsList += '--skip-cursor-fix' }
if ($PreferDirect) {
    $argsList += @('--prefer-direct', '--confirm', 'PREFER_DIRECT_WININET')
}

# Merge stderr (audit JSON lines) so PowerShell does not treat them as terminating errors.
$prevEap = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
$raw = & $Python @argsList 2>&1
$ErrorActionPreference = $prevEap
$json = ($raw | ForEach-Object { "$_" }) -join "`n"
Write-Host $json

if ($json -match '"outcome":\s*"healthy"') {
    Write-Host "OK: Proxy path is clean. Restart LinkedIn/browser if needed." -ForegroundColor Green
    exit 0
}
if ($json -match '"outcome":\s*"localhost_proxy_active"') {
    Write-Host "INFO: Localhost proxy still active. For LinkedIn, re-run with -PreferDirect." -ForegroundColor Yellow
    exit 0
}
if ($json -match '"outcome":\s*"still_dead"') {
    Write-Host "WARN: Still dead — try scripts\fix-wininet-proxy.cmd" -ForegroundColor Yellow
    exit 1
}
if ($json -match '"outcome":\s*"needs_prefer_direct_confirm"') {
    Write-Host "WARN: prefer-direct blocked — pass -PreferDirect to confirm." -ForegroundColor Yellow
    exit 1
}
if ($DryRun) {
    Write-Host "Dry-run complete (no changes applied)." -ForegroundColor Cyan
}
exit 0
