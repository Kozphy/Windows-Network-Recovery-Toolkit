#Requires -Version 5.1
<#
.SYNOPSIS
  One-shot automatic fix for dead localhost WinINET proxy (no prompts).
.DESCRIPTION
  Delegates to: python -m src auto-fix-proxy

  Steps (in Python orchestrator):
    1. configure-cursor-no-proxy.ps1
    2. proxy-guardian live clear (dead localhost only)
    3. proxy-fix fallback if still stale
    4. install-dead-proxy-guardian.ps1 background loop (60s default)

  Example:
    .\scripts\auto-fix-proxy.ps1
    .\scripts\auto-fix-proxy.ps1 -SkipGuardianInstall
    .\scripts\auto-fix-proxy.ps1 -DryRun
#>
param(
    [switch]$SkipGuardianInstall,
    [switch]$DryRun,
    [int]$IntervalSeconds = 60
)

$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Python = Join-Path $RepoRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $Python)) {
    $Python = (Get-Command python -ErrorAction Stop).Source
}

Set-Location -LiteralPath $RepoRoot
$env:PYTHONPATH = $RepoRoot

Write-Host "=== Auto-fix dead proxy (WNRT) ===" -ForegroundColor Cyan

$argsList = @('-m', 'src', 'auto-fix-proxy', '--json', '--guardian-interval', "$IntervalSeconds")
if ($SkipGuardianInstall) { $argsList += '--skip-guardian-install' }
if ($DryRun) { $argsList += '--dry-run' }

$json = & $Python @argsList 2>&1 | Out-String
Write-Host $json

if ($json -match '"outcome":\s*"healthy"') {
    Write-Host "OK: Proxy path is clean. Restart your browser." -ForegroundColor Green
    exit 0
}
if ($json -match '"outcome":\s*"still_dead"') {
    Write-Host "WARN: Still dead — try scripts\fix-wininet-proxy.cmd" -ForegroundColor Yellow
    exit 1
}
if ($DryRun) {
    Write-Host "Dry-run complete (no changes applied)." -ForegroundColor Cyan
}
exit 0
