@echo off
REM =============================================================================
REM diagnose_proxy.bat — Read-only snapshot of WinINET, WinHTTP, Git, npm, user env.
REM SAFETY/PRIVILEGES: Runs as current user; no HKCU/network mutations.
REM AUDIT ARTIFACTS: Delegates reports\proxy_guard_report.txt to diagnose_proxy.ps1 resolution.
REM Output: reports/proxy_guard_report.txt  |  Windows 10/11  |  No mutations.
REM =============================================================================
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0diagnose_proxy.ps1"
set "ERR=%ERRORLEVEL%"
endlocal & exit /b %ERR%
