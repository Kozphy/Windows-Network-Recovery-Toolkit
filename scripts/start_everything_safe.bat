@echo off
setlocal
cd /d "%~dp0.."
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_everything_safe.ps1" %*
set EXITCODE=%ERRORLEVEL%
echo.
echo One-click launcher exited with code %EXITCODE%.
echo.
pause
exit /b %EXITCODE%
