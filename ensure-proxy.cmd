@echo off
REM Ensure proxy health when opening this repo (dead localhost clear + guardian install).
REM For LinkedIn reliability (force direct): ensure-proxy.cmd prefer-direct
cd /d "%~dp0"
if /I "%~1"=="prefer-direct" (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\ensure-proxy-health.ps1" -PreferDirect
) else (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\ensure-proxy-health.ps1"
)
