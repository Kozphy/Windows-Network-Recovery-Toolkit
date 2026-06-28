#Requires -Version 5.1
<#
.SYNOPSIS
  Background loop: invoke proxy-guardian --once every five minutes.
.DESCRIPTION
  Started hidden by install-dead-proxy-guardian.ps1 Startup hook.
  Calls windows_network_toolkit proxy-guardian --once; sleeps 300 seconds between checks.

  Inputs:  None (repo root inferred from script location)
  Outputs: Discarded JSON from guardian (Out-Null); no console UI

  Privileges:
    Current user; may mutate HKCU WinINET when DEAD_PROXY_CONFIG detected.

  Side effects:
    Repeated proxy-guardian checks; registry disable on dead proxy only.

  Safety boundaries:
    Same as proxy-guardian — no mutation unless DEAD_PROXY_CONFIG and no listener.

  Idempotency:
    Loop runs until process killed or -Uninstall on install-dead-proxy-guardian.ps1.

  Recovery:
    Stop-Process powershell instances with run-proxy-guardian-loop.ps1 in command line,
    or run install-dead-proxy-guardian.ps1 -Uninstall

  Example:
    powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run-proxy-guardian-loop.ps1
.NOTES
  Do not run multiple instances — install script stops existing loop before StartNow.
#>
$ErrorActionPreference = 'SilentlyContinue'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Python = Join-Path $RepoRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $Python)) {
    $Python = (Get-Command python -ErrorAction Stop).Source
}
Set-Location -LiteralPath $RepoRoot
while ($true) {
    & $Python -m windows_network_toolkit proxy-guardian --once | Out-Null
    Start-Sleep -Seconds 300
}
