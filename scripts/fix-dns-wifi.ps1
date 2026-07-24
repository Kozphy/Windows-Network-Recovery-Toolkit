#Requires -Version 5.1
<#
.SYNOPSIS
  Fix common Wi-Fi DNS_PROBE_FINISHED_BAD_CONFIG causes (mismatched / stale DNS).

.DESCRIPTION
  Observation: hosts on 192.168.68.x with primary DNS 192.168.1.1 often see
  browser DNS_PROBE_FINISHED_BAD_CONFIG even when intermittent Resolve-DnsName works.

  This script (prefer Run as Administrator):
    1. Flushes DNS cache
    2. Optionally clears HKCU WinINET localhost proxy (calls emergency clear)
    3. Sets Wi-Fi DNS to gateway (if detectable) + 1.1.1.1 + 8.8.8.8

  Does NOT kill processes, reset firewall, or disable adapters.

.EXAMPLE
  # Elevated:
  .\scripts\fix-dns-wifi.ps1
  .\scripts\fix-dns-wifi.ps1 -InterfaceAlias Wi-Fi -Json
#>
param(
    [string]$InterfaceAlias = 'Wi-Fi',
    [switch]$SkipProxyClear,
    [switch]$Json,
    [string[]]$DnsServers = @()
)

$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

function Test-IsAdmin {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    $p = New-Object Security.Principal.WindowsPrincipal($id)
    return $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

$result = [ordered]@{
    schema_version = 1
    action         = 'fix_dns_wifi'
    interface      = $InterfaceAlias
    elevated       = (Test-IsAdmin)
    before_dns     = @()
    after_dns      = @()
    gateway        = $null
    ipv4           = $null
    flushed_dns    = $false
    proxy_cleared  = $false
    outcome        = 'error'
    limitations    = @(
        'Requires elevation to change adapter DNS.',
        'Does not prove which process set bad DNS.',
        'Browser may need Refresh / restart after DNS change.',
        'Corporate NRPT / DoH policy may override these settings.'
    )
}

$cfg = Get-NetIPConfiguration -InterfaceAlias $InterfaceAlias -ErrorAction SilentlyContinue
if (-not $cfg) {
    $result.outcome = 'interface_not_found'
    if ($Json) { $result | ConvertTo-Json -Compress -Depth 5; exit 1 }
    Write-Error "Interface '$InterfaceAlias' not found."
    exit 1
}

$result.ipv4 = [string]$cfg.IPv4Address.IPAddress
$result.gateway = [string]$cfg.IPv4DefaultGateway.NextHop
$result.before_dns = @((Get-DnsClientServerAddress -InterfaceAlias $InterfaceAlias -AddressFamily IPv4).ServerAddresses)

ipconfig /flushdns | Out-Null
$result.flushed_dns = $true

if (-not $SkipProxyClear) {
    $emerg = Join-Path $PSScriptRoot 'emergency-clear-wininet-proxy.ps1'
    if (Test-Path $emerg) {
        & powershell -NoProfile -ExecutionPolicy Bypass -File $emerg -Force -Json | Out-Null
        $result.proxy_cleared = $true
    }
}

if (-not (Test-IsAdmin)) {
    $result.outcome = 'needs_elevation'
    if ($Json) { $result | ConvertTo-Json -Compress -Depth 5; exit 2 }
    Write-Host "Elevation required to set DNS on '$InterfaceAlias'." -ForegroundColor Yellow
    Write-Host "Before DNS: $($result.before_dns -join ', ')" -ForegroundColor DarkGray
    Write-Host "Re-run elevated, or approve UAC if a prompt appears." -ForegroundColor Cyan
    # Relaunch self elevated
    $arg = "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`" -InterfaceAlias `"$InterfaceAlias`""
    if ($SkipProxyClear) { $arg += ' -SkipProxyClear' }
    if ($Json) { $arg += ' -Json' }
    Start-Process -FilePath powershell.exe -Verb RunAs -ArgumentList $arg -Wait
    exit 0
}

if ($DnsServers.Count -eq 0) {
    $servers = New-Object System.Collections.Generic.List[string]
    if ($result.gateway) { [void]$servers.Add([string]$result.gateway) }
    foreach ($s in @('1.1.1.1', '8.8.8.8')) {
        if (-not $servers.Contains($s)) { [void]$servers.Add($s) }
    }
    $DnsServers = $servers.ToArray()
}

Set-DnsClientServerAddress -InterfaceAlias $InterfaceAlias -ServerAddresses $DnsServers
ipconfig /flushdns | Out-Null
$result.after_dns = @((Get-DnsClientServerAddress -InterfaceAlias $InterfaceAlias -AddressFamily IPv4).ServerAddresses)
$result.outcome = 'dns_updated'

# Light probe
try {
    $null = Resolve-DnsName 'tw.download.nvidia.com' -ErrorAction Stop
    $result.nvidia_resolve_ok = $true
} catch {
    $result.nvidia_resolve_ok = $false
    $result.nvidia_resolve_error = $_.Exception.Message
}

if ($Json) {
    $result | ConvertTo-Json -Compress -Depth 5
} else {
    Write-Host "OK: DNS on $InterfaceAlias -> $($result.after_dns -join ', ')" -ForegroundColor Green
    Write-Host "Flushed DNS. Fully quit and reopen the browser, then Refresh the NVIDIA page." -ForegroundColor Cyan
    if ($result.nvidia_resolve_ok) {
        Write-Host "Resolve tw.download.nvidia.com: OK" -ForegroundColor Green
    } else {
        Write-Host "Resolve tw.download.nvidia.com: FAIL ($($result.nvidia_resolve_error))" -ForegroundColor Yellow
    }
}
exit 0
