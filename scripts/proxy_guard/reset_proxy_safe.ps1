#Requires -Version 5.1
<#
.SYNOPSIS
  User-confirmed rollback of common user-scope proxy settings (WinINET, WinHTTP, Git, npm, optional user env).
.NOTES
  Does not change firewall or adapters.
  User-scope env vars cleared only after typing CLEAR; Machine-scope only after ADVANCED (may need elevation).
  Appends JSON lines to reports/proxy_guard_actions.jsonl (compact metadata only).
#>

$ErrorActionPreference = 'SilentlyContinue'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = (Resolve-Path (Join-Path $ScriptDir '..\..')).Path
$ReportDir = Join-Path $RepoRoot 'reports'
if (-not (Test-Path $ReportDir)) { New-Item -ItemType Directory -Path $ReportDir -Force | Out-Null }
$LogFile = Join-Path $ReportDir 'proxy_guard_actions.jsonl'

function Write-ActionLog {
    param([string]$Action, [string]$Result, [string]$Note = '')
    $row = [ordered]@{
        schema_version = 1
        timestamp_utc  = [datetime]::UtcNow.ToString('o')
        action         = $Action
        result         = $Result
        note           = $Note
    } | ConvertTo-Json -Compress -Depth 3
    Add-Content -LiteralPath $LogFile -Value $row -Encoding utf8
}

Write-Host ''
Write-Host '=== Proxy Guard — reset_proxy_safe ===' -ForegroundColor Cyan
Write-Host 'This will modify YOUR USER proxy settings: HKCU WinINET, WinHTTP, Git global, npm,' -ForegroundColor Yellow
Write-Host 'and optionally User-scope HTTP_PROXY / HTTPS_PROXY / ALL_PROXY.' -ForegroundColor Yellow
Write-Host 'Firewall, adapters, and Machine environment are not modified.' -ForegroundColor DarkGray
Write-Host ''
$yn = Read-Host 'Type YES to proceed with the safe reset'
if ($yn -cne 'YES') {
    Write-Host 'Aborted (no changes).'
    exit 0
}

& reg.exe add "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyEnable /t REG_DWORD /d 0 /f | Out-Null
if ($LASTEXITCODE -eq 0) { Write-ActionLog -Action 'hkcu_proxyenable_zero' -Result 'ok' } else { Write-ActionLog -Action 'hkcu_proxyenable_zero' -Result 'error' -Note "exit $LASTEXITCODE" }

& reg.exe delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyServer /f 2>$null | Out-Null
Write-ActionLog -Action 'hkcu_proxyserver_delete' -Result 'attempted'

$null = & netsh.exe winhttp reset proxy 2>&1
Write-ActionLog -Action 'winhttp_reset_proxy' -Result 'ok' -Note 'netsh winhttp reset proxy executed'

$git = Get-Command git -ErrorAction SilentlyContinue
if ($git) {
    & git.exe config --global --unset-all http.proxy 2>$null
    & git.exe config --global --unset-all https.proxy 2>$null
    Write-ActionLog -Action 'git_global_unset' -Result 'ok'
} else {
    Write-ActionLog -Action 'git_global_unset' -Result 'skipped' -Note 'git not on path'
}

$npm = Get-Command npm -ErrorAction SilentlyContinue
if ($npm) {
    & npm.exe config delete proxy 2>$null
    & npm.exe config delete https-proxy 2>$null
    Write-ActionLog -Action 'npm_config_delete' -Result 'ok'
} else {
    Write-ActionLog -Action 'npm_config_delete' -Result 'skipped' -Note 'npm not on path'
}

Write-Host ''
$envYn = Read-Host 'Clear USER-scope HTTP_PROXY, HTTPS_PROXY, and ALL_PROXY? (type CLEAR to confirm)'
if ($envYn -ceq 'CLEAR') {
    foreach ($n in @('HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY')) {
        [Environment]::SetEnvironmentVariable($n, $null, 'User')
    }
    Write-ActionLog -Action 'user_env_proxy_cleared' -Result 'ok' -Note 'User scope only'
    Write-Host 'Cleared user-scope HTTP_PROXY / HTTPS_PROXY / ALL_PROXY.' -ForegroundColor Green
} else {
    Write-ActionLog -Action 'user_env_proxy_cleared' -Result 'skipped' -Note 'operator declined'
    Write-Host 'Skipped user environment clearing.' -ForegroundColor DarkYellow
}

Write-Host ''
Write-Host 'Advanced (optional): Machine-scope HTTP_PROXY / HTTPS_PROXY / ALL_PROXY — rarely needed; requires Administrator.' -ForegroundColor DarkGray
$adv = Read-Host 'Type ADVANCED only if you must clear system-level proxy env vars (else press Enter to skip)'
if ($adv -ceq 'ADVANCED') {
    try {
        foreach ($n in @('HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY')) {
            [Environment]::SetEnvironmentVariable($n, $null, 'Machine')
        }
        Write-ActionLog -Action 'machine_env_proxy_cleared' -Result 'ok' -Note 'HTTP_PROXY HTTPS_PROXY ALL_PROXY'
        Write-Host 'Machine-scope proxy env vars cleared (if process had rights).' -ForegroundColor Green
    } catch {
        Write-ActionLog -Action 'machine_env_proxy_cleared' -Result 'error' -Note $_.Exception.Message
        Write-Warning 'Could not clear Machine environment (run elevated or edit System Properties > Environment).'
    }
} else {
    Write-ActionLog -Action 'machine_env_proxy_cleared' -Result 'skipped' -Note 'not requested'
}

Write-Host ''
Write-Host "Done. Actions appended to: $LogFile" -ForegroundColor Cyan
exit 0
