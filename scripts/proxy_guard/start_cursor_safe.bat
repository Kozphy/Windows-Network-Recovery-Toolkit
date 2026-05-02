@echo off
REM =============================================================================
REM start_cursor_safe.bat — Diagnose -> optional guided reset_proxy_safe -> Cursor launch
REM SAFETY: Diagnose step is read-only; reset_proxy_safe.bat mutates HKCU/WinHTTP only after YES.
REM OUTPUT: Inherited from diagnose_proxy.bat & reset_proxy_safe.ps1 logs under reports\.
REM PRIVILEGES: Runs as current user; escalation only if Cursor install path demands it (rare).
REM =============================================================================
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_cursor_safe.ps1"
set "ERR=%ERRORLEVEL%"
endlocal & exit /b %ERR%
