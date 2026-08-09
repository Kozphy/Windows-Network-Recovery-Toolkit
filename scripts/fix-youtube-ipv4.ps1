#Requires -Version 5.1
<#
.SYNOPSIS
  Fix YouTube stalling when IPv6 path is broken but IPv4 works.
.DESCRIPTION
  Sets Prefer IPv4 over IPv6 (DisabledComponents=0x20) and disables IPv6
  on the Wi-Fi adapter for immediate effect. Requires Administrator.
#>
param(
    [switch]$Revert
)

$ErrorActionPreference = 'Stop'
$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator
)
if (-not $admin) {
    Write-Host 'ERROR: Run as Administrator (UAC).' -ForegroundColor Red
    exit 2
}

$p = 'HKLM:\SYSTEM\CurrentControlSet\Services\Tcpip6\Parameters'
if (-not (Test-Path $p)) { New-Item -Path $p -Force | Out-Null }

if ($Revert) {
    Remove-ItemProperty -Path $p -Name DisabledComponents -ErrorAction SilentlyContinue
    Enable-NetAdapterBinding -Name 'Wi-Fi' -ComponentID ms_tcpip6 -ErrorAction SilentlyContinue
    Write-Host 'Reverted Prefer-IPv4 registry and re-enabled Wi-Fi IPv6 (if present).' -ForegroundColor Green
} else {
    New-ItemProperty -Path $p -Name DisabledComponents -PropertyType DWord -Value 0x20 -Force | Out-Null
    Write-Host 'Set DisabledComponents=0x20 (Prefer IPv4 over IPv6).' -ForegroundColor Green
    if (Get-NetAdapter -Name 'Wi-Fi' -ErrorAction SilentlyContinue) {
        Disable-NetAdapterBinding -Name 'Wi-Fi' -ComponentID ms_tcpip6 -ErrorAction Stop
        Write-Host 'Disabled IPv6 binding on Wi-Fi (immediate).' -ForegroundColor Green
    }
}

ipconfig /flushdns | Out-Null
Write-Host '=== Verify ==='
curl.exe -4 -s -o NUL -w 'ipv4_youtube=%{http_code} time=%{time_total}\n' --connect-timeout 10 https://www.youtube.com/generate_204
curl.exe -s -o NUL -w 'default_youtube=%{http_code} time=%{time_total}\n' --connect-timeout 10 https://www.youtube.com/generate_204
Write-Host 'Done. Hard-refresh YouTube (Ctrl+Shift+R) or restart the browser.' -ForegroundColor Cyan
if (-not $Revert) {
    Write-Host 'Optional reboot makes Prefer-IPv4 apply to all adapters permanently.' -ForegroundColor Yellow
    Write-Host 'Revert later: .\scripts\fix-youtube-ipv4.ps1 -Revert' -ForegroundColor Yellow
}
