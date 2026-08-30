@echo off
REM =============================================================================
REM fix-dns.cmd — elevate and repair Wi-Fi DNS (DNS_PROBE_FINISHED_BAD_CONFIG)
REM =============================================================================
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\fix-dns-wifi.ps1" %*
exit /b %ERRORLEVEL%
