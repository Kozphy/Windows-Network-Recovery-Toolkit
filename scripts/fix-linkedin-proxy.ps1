#Requires -Version 5.1
<#
.SYNOPSIS
  One-shot LinkedIn / browser relief for WinINET localhost proxy timeouts.

.DESCRIPTION
  1. configure-cursor-no-proxy.ps1 (stop Cursor rewriting system proxy)
  2. Clear WinINET via emergency-clear-wininet-proxy.ps1 (no Python required)
     — or ensure-proxy-health -PreferDirect when Python is available
  3. Optionally install dead+broken guardian loop for recurrence protection

.EXAMPLE
  .\scripts\fix-linkedin-proxy.ps1
  .\scripts\fix-linkedin-proxy.ps1 -SkipGuardianInstall
  .\scripts\fix-linkedin-proxy.ps1 -DryRun
  .\fix-linkedin-proxy.cmd
#>
param(
    [switch]$SkipGuardianInstall,
    [switch]$SkipCursorFix,
    [switch]$DryRun,
    [switch]$PreferPythonEnsure,
    [int]$IntervalSeconds = 60
)

$ErrorActionPreference = 'Continue'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location -LiteralPath $RepoRoot
$env:PYTHONPATH = $RepoRoot

$Python = Join-Path $RepoRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $Python)) {
    $portable = Join-Path $RepoRoot '.tools\python312\python.exe'
    if (Test-Path -LiteralPath $portable) {
        $Python = $portable
    } else {
        $cmd = Get-Command python -ErrorAction SilentlyContinue
        if ($cmd) { $Python = $cmd.Source } else { $Python = $null }
    }
}

Write-Host "=== LinkedIn / WinINET prefer-direct relief (WNRT) ===" -ForegroundColor Cyan

$steps = @()

if (-not $SkipCursorFix -and -not $DryRun) {
    $cursorScript = Join-Path $PSScriptRoot 'configure-cursor-no-proxy.ps1'
    if (Test-Path -LiteralPath $cursorScript) {
        Write-Host "--- Cursor no-proxy ---" -ForegroundColor DarkCyan
        & powershell -NoProfile -ExecutionPolicy Bypass -File $cursorScript
        $steps += @{ step = 'cursor_no_proxy'; exit = $LASTEXITCODE }
    } else {
        $steps += @{ step = 'cursor_no_proxy'; skipped = $true }
    }
}

$cleared = $false
if ($PreferPythonEnsure -and $Python -and -not $DryRun) {
    Write-Host "--- ensure-proxy-health -PreferDirect ---" -ForegroundColor DarkCyan
    & $Python -m src ensure-proxy-health --prefer-direct --confirm PREFER_DIRECT_WININET --json --skip-cursor-fix 2>&1 | Out-Host
    if ($LASTEXITCODE -eq 0) { $cleared = $true }
    $steps += @{ step = 'ensure_prefer_direct'; exit = $LASTEXITCODE }
}

if (-not $cleared) {
    Write-Host "--- emergency-clear-wininet-proxy ---" -ForegroundColor DarkCyan
    $emerg = Join-Path $PSScriptRoot 'emergency-clear-wininet-proxy.ps1'
    $emergArgs = @('-Force')
    if ($DryRun) { $emergArgs = @('-WhatIf', '-Json') }
    else { $emergArgs += '-Json' }
    $json = & powershell -NoProfile -ExecutionPolicy Bypass -File $emerg @emergArgs 2>&1 | Out-String
    Write-Host $json
    $steps += @{ step = 'emergency_clear'; output = $json.Trim() }
    if ($json -match '"outcome":\s*"(cleared|already_direct)"') { $cleared = $true }
}

if (-not $SkipGuardianInstall -and -not $DryRun) {
    Write-Host "--- install dead+broken guardian loop ---" -ForegroundColor DarkCyan
    $install = Join-Path $PSScriptRoot 'install-dead-proxy-guardian.ps1'
    if (Test-Path -LiteralPath $install) {
        & powershell -NoProfile -ExecutionPolicy Bypass -File $install -IntervalSeconds $IntervalSeconds
        $steps += @{ step = 'guardian_install'; exit = $LASTEXITCODE }
    } else {
        $steps += @{ step = 'guardian_install'; skipped = $true }
    }
}

$pe = (Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -EA SilentlyContinue).ProxyEnable
$ps = (Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -EA SilentlyContinue).ProxyServer
Write-Host ""
Write-Host "WinINET now: ProxyEnable=$pe ProxyServer=$ps" -ForegroundColor $(if ([int]$pe -eq 0) { 'Green' } else { 'Yellow' })
Write-Host "Fully quit and reopen LinkedIn (and browser) so settings reload." -ForegroundColor Cyan

if ($cleared -or [int]$pe -eq 0) {
    Write-Host "OK: Prefer-direct path applied." -ForegroundColor Green
    exit 0
}
Write-Host "WARN: Proxy may still be enabled — re-run with admin PowerShell or check GPO." -ForegroundColor Yellow
exit 1
