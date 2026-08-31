@echo off
setlocal EnableExtensions
REM ============================================================
REM WNRT Emergency WinINET Proxy Reset (HKCU)
REM Purpose:     Immediate browser/LinkedIn relief (ERR_PROXY / timeout)
REM Privileges:  Current user (HKCU Internet Settings)
REM Side effects: ProxyEnable=0; clears ProxyServer
REM Safety:      Prefer scripts\run_src.py proxy-fix; falls back to PowerShell
REM Examples:
REM   scripts\fix-wininet-proxy.cmd
REM   scripts\fix-wininet-proxy.cmd /Y
REM   scripts\fix-wininet-proxy.cmd -Force
REM ============================================================
title WNRT Emergency WinINET Proxy Reset

set "REPO_ROOT=%~dp0.."
pushd "%REPO_ROOT%" >nul 2>&1

set "FORCE="
if /I "%~1"=="/Y" set "FORCE=1"
if /I "%~1"=="/y" set "FORCE=1"
if /I "%~1"=="-Force" set "FORCE=1"
if /I "%~1"=="--force" set "FORCE=1"
if /I "%~1"=="-Y" set "FORCE=1"

set "PYTHON="
if exist ".venv\Scripts\python.exe" set "PYTHON=.venv\Scripts\python.exe"
if not defined PYTHON if exist ".tools\python312\python.exe" set "PYTHON=.tools\python312\python.exe"
if not defined PYTHON (
  where python >nul 2>&1 && set "PYTHON=python"
)

echo.
echo ============================================================
echo   EMERGENCY: Disable current-user WinINET proxy (HKCU)
echo ============================================================
echo.
echo WARNING: This disables YOUR user WinINET proxy settings.
echo          Use when the browser/LinkedIn shows ERR_PROXY / timeout.
echo.

if not defined FORCE (
  echo          For ongoing protection after relief:
  echo            .\scripts\run_src.py proxy-guardian --once --clear-broken --confirm-broken PREFER_DIRECT_WININET --dry-run false
  echo            scripts\fix-linkedin-proxy.ps1
  echo.
  echo Press Ctrl+C to cancel, or
  pause
)

set "RC=1"
if defined PYTHON (
  echo Using repo-safe Python launcher...
  "%PYTHON%" "%~dp0run_src.py" proxy-fix --confirm DISABLE_WININET_PROXY --dry-run false
  set "RC=%ERRORLEVEL%"
) else (
  echo Python not found — using PowerShell emergency clear...
  set "RC=1"
)

if %RC% neq 0 (
  echo.
  echo Python proxy-fix failed or was blocked. Falling back to scripts\emergency-clear-wininet-proxy.ps1 ...
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0emergency-clear-wininet-proxy.ps1" -Force
  set "RC=%ERRORLEVEL%"
)

echo.
if %RC% equ 0 (
  echo OK: Restart LinkedIn / browser ^(fully quit and reopen^).
) else (
  echo WARN: Clear may have failed — check output above.
)
echo Audit: reports\proxy_guard_actions.jsonl / logs\proxy_guardian.jsonl
echo.

if not defined FORCE pause
popd
endlocal & exit /b %RC%
