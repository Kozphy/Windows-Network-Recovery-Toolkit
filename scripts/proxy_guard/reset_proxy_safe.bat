@echo off
REM =============================================================================
REM reset_proxy_safe.bat — User-confirmed proxy cleanup (HKCU WinINET, WinHTTP,
REM Git, npm, optional user env). Logs JSON lines to reports/proxy_guard_actions.jsonl
REM SAFETY: Mutations begin only inside reset_proxy_safe.ps1 after typed YES confirmation.
REM PRIVILEGES: Current user scope by default (ADVANCED path may elevate depending on ops).
REM Requires PowerShell 5.1+. Never touches firewall or adapters.
REM =============================================================================
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0reset_proxy_safe.ps1"
set "ERR=%ERRORLEVEL%"
endlocal & exit /b %ERR%
