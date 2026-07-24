#Requires -Version 5.1
<#
.SYNOPSIS
  One-shot automatic fix for dead/active localhost WinINET proxy (no prompts).
.DESCRIPTION
  Delegates to: python -m src auto-fix-proxy (or scripts/run_src.py)

  Steps (in Python orchestrator):
    1. configure-cursor-no-proxy.ps1
    2. proxy-guardian live clear (dead + broken + prefer-direct paths)
    3. proxy-fix fallback if still stale
    4. install-dead-proxy-guardian.ps1 background loop (15s hold-direct default)

  Prefer set-and-forget: ..\enable-proxy-autofix.cmd

  Example:
    .\scripts\auto-fix-proxy.ps1
    .\scripts\auto-fix-proxy.ps1 -PreferDirect
    .\scripts\auto-fix-proxy.ps1 -SkipGuardianInstall
    .\scripts\auto-fix-proxy.ps1 -DryRun
#>
param(
    [switch]$SkipGuardianInstall,
    [switch]$DryRun,
    [switch]$PreferDirect,
    [int]$IntervalSeconds = 15
)

$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Python = Join-Path $RepoRoot '.venv\Scripts\python.exe'
$Runner = Join-Path $PSScriptRoot 'run_src.py'
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

Write-Host "=== Auto-fix dead/active localhost proxy (WNRT) ===" -ForegroundColor Cyan

$argsList = @($Runner, 'auto-fix-proxy', '--json', '--guardian-interval', "$IntervalSeconds")
if ($SkipGuardianInstall) { $argsList += '--skip-guardian-install' }
if ($DryRun) { $argsList += '--dry-run' }
if ($PreferDirect) {
    $argsList += @('--prefer-direct', '--confirm', 'PREFER_DIRECT_WININET')
}

$json = & $Python @argsList 2>&1 | Out-String
Write-Host $json

if ($json -match '"outcome":\s*"healthy"') {
    Write-Host "OK: Proxy path is clean. Restart your browser (and Cursor if open)." -ForegroundColor Green
    exit 0
}
if ($json -match '"outcome":\s*"still_dead"') {
    Write-Host "WARN: Still dead — try scripts\fix-wininet-proxy.cmd" -ForegroundColor Yellow
    exit 1
}
if ($json -match '"outcome":\s*"needs_prefer_direct_confirm"') {
    Write-Host "WARN: Confirm required — re-run with -PreferDirect (active or active-but-broken proxy)" -ForegroundColor Yellow
    exit 1
}
if ($json -match '"outcome":\s*"localhost_proxy_broken"') {
    Write-Host "WARN: Active-but-broken localhost proxy — re-run with -PreferDirect" -ForegroundColor Yellow
    exit 1
}
if ($json -match '"outcome":\s*"localhost_proxy_active"') {
    Write-Host "WARN: Localhost proxy still active — re-run with -PreferDirect" -ForegroundColor Yellow
    exit 1
}
if ($DryRun) {
    Write-Host "Dry-run complete (no changes applied)." -ForegroundColor Cyan
}
exit 0

