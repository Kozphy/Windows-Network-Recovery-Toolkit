#Requires -Version 5.1
<#
.SYNOPSIS
  Background loop: auto-clear dead / broken / localhost rewrite (hold-direct).
.DESCRIPTION
  Started by install-dead-proxy-guardian.ps1 (Startup hook).
  Uses scripts/run_src.py so embeddable/.tools Python works.

  Also runs a PowerShell emergency clear fallback when WinINET points at
  localhost — so autofix continues even if Python fails.

  Single-instance lock prevents duplicate loops.
  Heartbeat: reports/proxy_guardian_heartbeat.json
#>
param(
    [int]$IntervalSeconds = 15
)

$ErrorActionPreference = 'SilentlyContinue'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$ReportDir = Join-Path $RepoRoot 'reports'
if (-not (Test-Path $ReportDir)) {
    New-Item -ItemType Directory -Path $ReportDir -Force | Out-Null
}
$LockFile = Join-Path $ReportDir 'proxy_guardian_loop.lock'
$Heartbeat = Join-Path $ReportDir 'proxy_guardian_heartbeat.json'
$Emerg = Join-Path $PSScriptRoot 'emergency-clear-wininet-proxy.ps1'

# Single-instance: if another loop holds a live lock, exit.
if (Test-Path -LiteralPath $LockFile) {
    try {
        $prev = Get-Content -LiteralPath $LockFile -Raw | ConvertFrom-Json
        $prevPid = [int]$prev.pid
        if ($prevPid -gt 0 -and (Get-Process -Id $prevPid -ErrorAction SilentlyContinue)) {
            exit 0
        }
    } catch { }
}
@{ pid = $PID; started_utc = [datetime]::UtcNow.ToString('o'); repo = $RepoRoot } |
    ConvertTo-Json -Compress |
    Set-Content -LiteralPath $LockFile -Encoding utf8

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
$Runner = Join-Path $PSScriptRoot 'run_src.py'
Set-Location -LiteralPath $RepoRoot
$env:PYTHONPATH = $RepoRoot
$interval = [Math]::Max(5, $IntervalSeconds)

function Write-Heartbeat {
    param(
        [string]$Outcome,
        [int]$ProxyEnable,
        [string]$ProxyServer,
        [string]$Note = ''
    )
    $row = [ordered]@{
        schema_version = 1
        timestamp_utc  = [datetime]::UtcNow.ToString('o')
        pid            = $PID
        interval_s     = $interval
        outcome        = $Outcome
        proxy_enable   = $ProxyEnable
        proxy_server   = $ProxyServer
        note           = $Note
        hold_direct    = $true
    } | ConvertTo-Json -Compress
    Set-Content -LiteralPath $Heartbeat -Value $row -Encoding utf8
}

function Clear-LocalhostWinInetFallback {
    $reg = Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -ErrorAction SilentlyContinue
    $pe = if ($null -ne $reg.ProxyEnable) { [int]$reg.ProxyEnable } else { 0 }
    $ps = [string]$reg.ProxyServer
    if ($pe -ne 1) {
        return @{ cleared = $false; proxy_enable = $pe; proxy_server = $ps; reason = 'already_direct' }
    }
    if ($ps -notmatch '(?i)(127\.0\.0\.1|localhost|\[::1\])') {
        return @{ cleared = $false; proxy_enable = $pe; proxy_server = $ps; reason = 'non_localhost' }
    }
    if (Test-Path -LiteralPath $Emerg) {
        & powershell -NoProfile -ExecutionPolicy Bypass -File $Emerg -Force -Json | Out-Null
    } else {
        reg.exe add 'HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings' /v ProxyEnable /t REG_DWORD /d 0 /f | Out-Null
        reg.exe delete 'HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings' /v ProxyServer /f 2>$null | Out-Null
    }
    $after = Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -ErrorAction SilentlyContinue
    $ape = if ($null -ne $after.ProxyEnable) { [int]$after.ProxyEnable } else { 0 }
    return @{
        cleared = ($ape -eq 0)
        proxy_enable = $ape
        proxy_server = [string]$after.ProxyServer
        reason = 'fallback_clear'
    }
}

try {
    while ($true) {
        $pyOk = $false
        $pyNote = ''
        if ($Python -and (Test-Path -LiteralPath $Runner)) {
            & $Python $Runner proxy-guardian --once `
                --confirm CLEAR_DEAD_LOCALHOST_PROXY `
                --clear-broken `
                --hold-direct `
                --confirm-broken PREFER_DIRECT_WININET `
                --dry-run false `
                --json 2>$null | Out-Null
            $pyOk = ($LASTEXITCODE -eq 0)
            if (-not $pyOk) { $pyNote = "python_exit_$LASTEXITCODE" }
        } else {
            $pyNote = 'python_or_runner_missing'
        }

        # Always apply PS fallback for localhost rewrite (covers Python/_pth failures).
        $fb = Clear-LocalhostWinInetFallback
        $reg = Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -ErrorAction SilentlyContinue
        $pe = if ($null -ne $reg.ProxyEnable) { [int]$reg.ProxyEnable } else { 0 }
        $ps = [string]$reg.ProxyServer
        $outcome = if ($fb.cleared) { 'cleared_fallback' } elseif ($pyOk) { 'python_ok' } else { 'idle_or_error' }
        Write-Heartbeat -Outcome $outcome -ProxyEnable $pe -ProxyServer $ps -Note $pyNote

        Start-Sleep -Seconds $interval
    }
} finally {
    if (Test-Path -LiteralPath $LockFile) {
        try {
            $cur = Get-Content -LiteralPath $LockFile -Raw | ConvertFrom-Json
            if ([int]$cur.pid -eq $PID) {
                Remove-Item -LiteralPath $LockFile -Force -ErrorAction SilentlyContinue
            }
        } catch {
            Remove-Item -LiteralPath $LockFile -Force -ErrorAction SilentlyContinue
        }
    }
}
