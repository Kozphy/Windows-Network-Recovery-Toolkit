#Requires -Version 5.1
<#
.SYNOPSIS
  Python-free emergency clear of current-user WinINET proxy (HKCU).

.DESCRIPTION
  Sets ProxyEnable=0 and deletes ProxyServer when it points at localhost / is set.
  Calls InternetSetOption SETTINGS_CHANGED + REFRESH so browsers pick up the change.
  Appends a compact JSON line to reports/proxy_guard_actions.jsonl.

  Does NOT require Python. Does not kill processes, reset firewall, or touch WinHTTP
  unless -AlsoResetWinHttp is passed.

.EXAMPLE
  .\scripts\emergency-clear-wininet-proxy.ps1
  .\scripts\emergency-clear-wininet-proxy.ps1 -Force
  .\scripts\emergency-clear-wininet-proxy.ps1 -Json
#>
param(
    [switch]$Force,
    [switch]$Json,
    [switch]$AlsoResetWinHttp,
    [switch]$WhatIf
)

$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$ReportDir = Join-Path $RepoRoot 'reports'
if (-not (Test-Path $ReportDir)) {
    New-Item -ItemType Directory -Path $ReportDir -Force | Out-Null
}
$LogFile = Join-Path $ReportDir 'proxy_guard_actions.jsonl'
$RegPath = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings'

function Write-ActionLog {
    param([string]$Action, [string]$Result, [string]$Note = '')
    $row = [ordered]@{
        schema_version = 1
        timestamp_utc  = [datetime]::UtcNow.ToString('o')
        action         = $Action
        result         = $Result
        note           = $Note
        source         = 'emergency-clear-wininet-proxy.ps1'
    } | ConvertTo-Json -Compress -Depth 3
    Add-Content -LiteralPath $LogFile -Value $row -Encoding utf8
}

function Invoke-WinInetRefresh {
    try {
        Add-Type -Namespace WinInetEmergency -Name Native -MemberDefinition @'
[System.Runtime.InteropServices.DllImport("wininet.dll", SetLastError=true)]
public static extern bool InternetSetOption(System.IntPtr hInternet, int dwOption, System.IntPtr lpBuffer, int dwBufferLength);
'@ -ErrorAction Stop
        [void][WinInetEmergency.Native]::InternetSetOption([IntPtr]::Zero, 39, [IntPtr]::Zero, 0)
        [void][WinInetEmergency.Native]::InternetSetOption([IntPtr]::Zero, 37, [IntPtr]::Zero, 0)
        return $true
    } catch {
        return $false
    }
}

$before = Get-ItemProperty -Path $RegPath -ErrorAction SilentlyContinue
$beforeEnable = if ($null -ne $before.ProxyEnable) { [int]$before.ProxyEnable } else { 0 }
$beforeServer = [string]$before.ProxyServer

$result = [ordered]@{
    schema_version     = 1
    action             = 'emergency_clear_wininet'
    dry_run            = [bool]$WhatIf
    before_proxy_enable = $beforeEnable
    before_proxy_server = $beforeServer
    proxy_enable       = $beforeEnable
    proxy_server       = $beforeServer
    refreshed          = $false
    winhttp_reset      = $false
    outcome            = 'noop'
    limitations        = @(
        'HKCU WinINET only — not corporate GPO / machine proxy.',
        'Does not prove registry writer identity.',
        'Restart LinkedIn/browser after clear.'
    )
}

if ($beforeEnable -eq 0 -and [string]::IsNullOrWhiteSpace($beforeServer)) {
    $result.outcome = 'already_direct'
    Write-ActionLog -Action 'emergency_clear_wininet' -Result 'already_direct' -Note 'Proxy already disabled'
    if ($Json) { $result | ConvertTo-Json -Compress -Depth 4; exit 0 }
    Write-Host 'OK: WinINET already direct (ProxyEnable=0, no ProxyServer).' -ForegroundColor Green
    exit 0
}

if (-not $Force -and -not $WhatIf) {
    Write-Host 'This will disable YOUR user WinINET proxy (HKCU).' -ForegroundColor Yellow
    Write-Host "Current: ProxyEnable=$beforeEnable ProxyServer=$beforeServer" -ForegroundColor Yellow
    $yn = Read-Host 'Type YES to continue'
    if ($yn -cne 'YES') {
        $result.outcome = 'aborted'
        Write-ActionLog -Action 'emergency_clear_wininet' -Result 'aborted'
        if ($Json) { $result | ConvertTo-Json -Compress -Depth 4; exit 1 }
        Write-Host 'Aborted (no changes).'
        exit 1
    }
}

if ($WhatIf) {
    $result.outcome = 'would_clear'
    if ($Json) { $result | ConvertTo-Json -Compress -Depth 4; exit 0 }
    Write-Host "WhatIf: would set ProxyEnable=0 and clear ProxyServer='$beforeServer'" -ForegroundColor Cyan
    exit 0
}

reg.exe add 'HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings' /v ProxyEnable /t REG_DWORD /d 0 /f | Out-Null
if ($LASTEXITCODE -ne 0) {
    $result.outcome = 'error'
    Write-ActionLog -Action 'emergency_clear_wininet' -Result 'error' -Note "ProxyEnable reg exit $LASTEXITCODE"
    if ($Json) { $result | ConvertTo-Json -Compress -Depth 4; exit 1 }
    Write-Error 'Failed to set ProxyEnable=0'
    exit 1
}

if (-not [string]::IsNullOrWhiteSpace($beforeServer)) {
    reg.exe delete 'HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings' /v ProxyServer /f 2>$null | Out-Null
}

$result.refreshed = Invoke-WinInetRefresh

if ($AlsoResetWinHttp) {
    $null = & netsh.exe winhttp reset proxy 2>&1
    $result.winhttp_reset = $true
}

$after = Get-ItemProperty -Path $RegPath -ErrorAction SilentlyContinue
$result.proxy_enable = if ($null -ne $after.ProxyEnable) { [int]$after.ProxyEnable } else { 0 }
$result.proxy_server = [string]$after.ProxyServer
$result.outcome = if ($result.proxy_enable -eq 0) { 'cleared' } else { 'partial' }

Write-ActionLog -Action 'emergency_clear_wininet' -Result $result.outcome -Note "was enable=$beforeEnable server=$beforeServer"

if ($Json) {
    $result | ConvertTo-Json -Compress -Depth 4
} else {
    Write-Host "OK: WinINET cleared (ProxyEnable=$($result.proxy_enable)). Restart LinkedIn/browser." -ForegroundColor Green
    Write-Host "Log: $LogFile" -ForegroundColor DarkGray
}

if ($result.outcome -eq 'cleared') { exit 0 } else { exit 1 }
