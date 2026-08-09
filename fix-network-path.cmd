@echo off
REM Detect / fix broken IPv6 with healthy IPv4 (YouTube/browser stall class).
REM Preview:  fix-network-path.cmd
REM Apply:    fix-network-path.cmd /APPLY
REM Apply+YT: fix-network-path.cmd /APPLY /YOUTUBE
cd /d "%~dp0"

if /I "%~1"=="/APPLY" goto APPLY
if /I "%~1"=="APPLY" goto APPLY

echo === PREVIEW network-path-health ===
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\fix-network-path.ps1" -Json
echo.
echo To apply Prefer-IPv4: fix-network-path.cmd /APPLY
echo Browser stall only:   fix-youtube.cmd
exit /b %ERRORLEVEL%

:APPLY
set OPENYT=
if /I "%~2"=="/YOUTUBE" set OPENYT=-OpenYoutube
if /I "%~2"=="YOUTUBE" set OPENYT=-OpenYoutube
echo === APPLY Prefer-IPv4 (UAC) ===
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\fix-network-path.ps1" -Apply -Json %OPENYT%
exit /b %ERRORLEVEL%
