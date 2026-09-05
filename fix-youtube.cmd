@echo off
REM YouTube / Edge stall: Prefer-IPv4 path check + browser cold-start.
REM Do not use "timeout /t" here (fails when stdin is redirected).
cd /d "%~dp0"

echo === WNRT fix-youtube (delegates to path health + browser stall) ===
echo [1/2] Prefer-IPv4 / Happy-Eyeballs check (read-only)...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\fix-network-path.ps1" -Json

echo.
echo [2/2] Cold-start Edge/Chrome with --disable-quic (closes existing windows)...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\fix-browser-stall.ps1" -Apply -Json
echo.
echo Use the NEW browser window. If still spinning: fix-network-path.cmd /APPLY then this script again.
exit /b %ERRORLEVEL%
