@echo off
REM =============================================================================
REM ensure-proxy.cmd — repo-root wrapper for proxy health ensure
REM =============================================================================
REM Purpose:
REM   Run scripts\ensure-proxy-health.ps1 (dead localhost clear + guardian install).
REM Required privileges:
REM   Same as the PowerShell script / python -m src ensure-proxy-health path.
REM   PreferDirect may change WinINET toward direct access (policy-gated in Python).
REM Inputs:
REM   Optional first arg: prefer-direct  → passes -PreferDirect to the PS1.
REM Outputs:
REM   Console status from ensure-proxy-health.ps1 / Python CLI.
REM Side effects:
REM   May clear dead localhost proxy and install startup observability tasks.
REM Safety boundaries:
REM   Prefer dry-run via scripts\ensure-proxy-health.ps1 -DryRun for preview.
REM   Does not kill processes or reset firewall/adapters.
REM Idempotency:
REM   Re-running when already healthy should be a no-op or soft skip (see PS1/CLI).
REM Recovery:
REM   Re-run with -DryRun first; use toolkit proxy-status / proxy-disable --dry-run true.
REM Examples:
REM   ensure-proxy.cmd
REM   ensure-proxy.cmd prefer-direct
REM =============================================================================
cd /d "%~dp0"
if /I "%~1"=="prefer-direct" (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\ensure-proxy-health.ps1" -PreferDirect
) else (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\ensure-proxy-health.ps1"
)
