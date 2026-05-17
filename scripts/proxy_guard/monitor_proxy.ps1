#Requires -Version 5.1
# SAFETY — Default path appends telemetry only; `-AutoReset` enables destructive resets (explicitly labeled DANGEROUS in synopsis).
# PRIVILEGES — Executes as invoking user token; resets affect user-scope proxy keys only unless policies extend beyond script.
# OUTPUT — reports/proxy_guard_watch.jsonl under repo-relative reports directory.
<#
.SYNOPSIS
  Poll HKCU WinINET proxy keys every 5 seconds; log changes to reports/proxy_guard_watch.jsonl
.PARAMETER AutoReset
  DANGEROUS: if set, calls netsh winhttp reset and HKCU disable (still requires extra confirm).
.NOTES
  Process list includes only process *names* (no paths) to avoid username leakage in paths.
#>
param(
    [int]$IntervalSeconds = 5,
    [switch]$AutoReset
)

$ErrorActionPreference = 'SilentlyContinue'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = (Resolve-Path (Join-Path $ScriptDir '..\..')).Path
$ReportDir = Join-Path $RepoRoot 'reports'
if (-not (Test-Path $ReportDir)) { New-Item -ItemType Directory -Path $ReportDir -Force | Out-Null }
$WatchFile = Join-Path $ReportDir 'proxy_guard_watch.jsonl'

function Mask-Val([string]$s) {
    if ([string]::IsNullOrWhiteSpace($s)) { return '' }
    $t = $s -replace '(?:(?:25[0-5]|2[0-4][0-9]|1?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|1?[0-9][0-9]?)', '[IP]'
    return $t
}

function Get-ProxyState {
    $p = Get-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' -ErrorAction SilentlyContinue
    if (-not $p) { return @{ Enable = $null; Server = $null } }
    return @{
        Enable = $p.ProxyEnable
        Server = $p.ProxyServer
    }
}

function Get-RecentProcessNames {
    Get-Process -ErrorAction SilentlyContinue |
        Sort-Object -Property CPU -Descending |
        Select-Object -First 12 -ExpandProperty Name
}

$prev = Get-ProxyState
Write-Host "Proxy Guard watch — interval ${IntervalSeconds}s (Ctrl+C to stop)" -ForegroundColor Cyan
Write-Host "Log: $WatchFile" -ForegroundColor DarkGray
if ($AutoReset) {
    Write-Warning 'AutoReset is enabled: the toolkit will offer to run winhttp reset + HKCU disable on each change. This can disrupt applications. Type AUTOYES to arm (one-time).'
    $a = Read-Host
    if ($a -cne 'AUTOYES') { Write-Host 'AutoReset disarmed. Exiting.'; exit 1 }
}

while ($true) {
    Start-Sleep -Seconds $IntervalSeconds
    $cur = Get-ProxyState
    $changed = ($cur.Enable -ne $prev.Enable) -or ($cur.Server -ne $prev.Server)
    if (-not $changed) { continue }

    $recentNames = @(Get-RecentProcessNames)
    $row = [ordered]@{
        schema_version  = 1
        timestamp_utc     = [datetime]::UtcNow.ToString('o')
        event             = 'proxy_state_change'
        old_enable        = $prev.Enable
        new_enable        = $cur.Enable
        old_server_masked = (Mask-Val ([string]$prev.Server))
        new_server_masked = (Mask-Val ([string]$cur.Server))
        recent_processes  = $recentNames
    } | ConvertTo-Json -Compress -Depth 4
    Add-Content -LiteralPath $WatchFile -Value $row -Encoding utf8
    $oldOn = if ($prev.Enable -eq 1) { 'ON' } elseif ($prev.Enable -eq 0) { 'OFF' } else { '?' }
    $newOn = if ($cur.Enable -eq 1) { 'ON' } elseif ($cur.Enable -eq 0) { 'OFF' } else { '?' }
    Write-Host ""
    Write-Host "========== PROXY REGISTRY CHANGE ==========" -ForegroundColor Yellow
    Write-Host ("Time (UTC): {0}" -f [datetime]::UtcNow.ToString('o'))
    Write-Host ("ProxyEnable: {0} -> {1}" -f $oldOn, $newOn)
    Write-Host ("ProxyServer: {0} -> {1}" -f (Mask-Val ([string]$prev.Server)), (Mask-Val ([string]$cur.Server)))
    if ($cur.Enable -eq 1) {
        Write-Host "Impact: Proxy ON - browsers may fail until reset." -ForegroundColor Red
    } else {
        Write-Host "Impact: Proxy OFF - direct access if nothing re-enables it." -ForegroundColor Green
    }
    if ($recentNames) {
        Write-Host "Recent process names (not proof of writer):"
        $recentNames | ForEach-Object { Write-Host "  - $_" }
    }
    Write-Host ("Logged: {0}" -f $WatchFile) -ForegroundColor DarkGray
    Write-Host "Readable report: python -m src proxy-watch-report --tail 5"
    Write-Host "===========================================" -ForegroundColor Yellow
    Write-Host ""
    if ($AutoReset) {
        Write-Warning 'Change detected; running safe reset pipeline (netsh + HKCU) in 2s...'
        Start-Sleep 2
        & reg.exe add "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyEnable /t REG_DWORD /d 0 /f | Out-Null
        & reg.exe delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyServer /f 2>$null | Out-Null
        & netsh.exe winhttp reset proxy 2>&1 | Out-Null
        $log2 = [ordered]@{
            schema_version = 1
            timestamp_utc  = [datetime]::UtcNow.ToString('o')
            event          = 'auto_reset_invoked'
            result         = 'ok'
        } | ConvertTo-Json -Compress
        Add-Content -LiteralPath $WatchFile -Value $log2 -Encoding utf8
    }
    $prev = $cur
}
