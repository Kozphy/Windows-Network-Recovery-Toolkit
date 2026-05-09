@echo off
setlocal
cd /d "%~dp0.."
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0stop_everything_safe.ps1" %*
set EXITCODE=%ERRORLEVEL%
echo.
echo Stop launcher exited with code %EXITCODE%.
echo.
pause
exit /b %EXITCODE%
