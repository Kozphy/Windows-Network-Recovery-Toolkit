#Requires -Version 5.1
<#
.SYNOPSIS
  Prevent Cursor from managing Windows system proxy (root-cause fix for stale WinINET drift).
.DESCRIPTION
  Sets http.proxySupport to off in %APPDATA%\Cursor\User\settings.json.
  Preserves all other keys; does not modify WinINET registry directly.

  Inputs:  None
  Outputs: Console confirmation of previous and new http.proxySupport value

  Privileges:
    Current user only; writes Cursor user settings JSON.

  Side effects:
    Creates or updates settings.json under Cursor User profile.

  Safety boundaries:
    Does not change HKCU Internet Settings or WinHTTP. Restart Cursor after run.

  Idempotency:
    Setting http.proxySupport=off again is a no-op.

  Recovery:
    Manually set http.proxySupport back in Cursor settings if you rely on Cursor-managed proxy.

  Example:
    .\scripts\configure-cursor-no-proxy.ps1
.NOTES
  Engineering: addresses recurring DEAD_PROXY_CONFIG after Cursor exits without clearing proxy.
#>
$ErrorActionPreference = 'Stop'

$SettingsDir = Join-Path $env:APPDATA 'Cursor\User'
$SettingsPath = Join-Path $SettingsDir 'settings.json'
$Key = 'http.proxySupport'
$Value = 'off'

if (-not (Test-Path -LiteralPath $SettingsDir)) {
    New-Item -ItemType Directory -Path $SettingsDir -Force | Out-Null
}

$settings = [ordered]@{}
if (Test-Path -LiteralPath $SettingsPath) {
    $raw = Get-Content -LiteralPath $SettingsPath -Raw -ErrorAction Stop
    if (-not [string]::IsNullOrWhiteSpace($raw)) {
        $parsed = $raw | ConvertFrom-Json
        foreach ($prop in $parsed.PSObject.Properties) {
            $settings[$prop.Name] = $prop.Value
        }
    }
}

$previous = $settings[$Key]
$settings[$Key] = $Value

$json = ($settings | ConvertTo-Json -Depth 32)
[System.IO.File]::WriteAllText($SettingsPath, $json + [Environment]::NewLine, [System.Text.UTF8Encoding]::new($false))

Write-Host "Cursor settings updated: $SettingsPath" -ForegroundColor Green
if ($null -ne $previous -and "$previous" -ne $Value) {
    Write-Host "  $Key : $previous -> $Value"
} elseif ($null -eq $previous) {
    Write-Host "  $Key : (added) -> $Value"
} else {
    Write-Host "  $Key : already $Value"
}
Write-Host ""
Write-Host "Restart Cursor for this change to take effect." -ForegroundColor Cyan
