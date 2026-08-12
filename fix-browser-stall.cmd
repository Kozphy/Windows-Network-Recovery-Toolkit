@echo off
REM Chromium cold-start for IPv6/QUIC browser spin.
REM Preview:  fix-browser-stall.cmd
REM Apply:    fix-browser-stall.cmd /APPLY
cd /d "%~dp0"

if /I "%~1"=="/APPLY" goto APPLY
if /I "%~1"=="APPLY" goto APPLY

echo === PREVIEW fix-browser-stall (no browser kill) ===
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\fix-browser-stall.ps1" -Json
echo.
echo To restart Edge/Chrome with --disable-quic: fix-browser-stall.cmd /APPLY
echo Prefer-IPv4 first if needed:               fix-network-path.cmd /APPLY
exit /b %ERRORLEVEL%

:APPLY
echo === APPLY browser cold-start (closes Edge/Chrome) ===
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\fix-browser-stall.ps1" -Apply -Json
exit /b %ERRORLEVEL%
