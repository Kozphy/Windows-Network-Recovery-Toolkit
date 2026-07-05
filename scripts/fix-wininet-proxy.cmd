@echo off
setlocal
REM ============================================================
REM WNRT Emergency WinINET Proxy Reset (HKCU)
REM Purpose:     Immediate browser relief when ERR_PROXY_CONNECTION_FAILED
REM Privileges:  Current user (HKCU Internet Settings)
REM Side effects: ProxyEnable=0; clears localhost ProxyServer only
REM Safety:      Governed apply via python -m src proxy-fix
REM Example:     scripts\fix-wininet-proxy.cmd
REM ============================================================
title WNRT Emergency WinINET Proxy Reset

set "REPO_ROOT=%~dp0.."
pushd "%REPO_ROOT%" >nul 2>&1

set "PYTHON="
if exist ".venv\Scripts\python.exe" set "PYTHON=.venv\Scripts\python.exe"
if not defined PYTHON set "PYTHON=python"

echo.
echo ============================================================
echo   EMERGENCY: Disable current-user WinINET proxy (HKCU)
echo ============================================================
echo.
echo WARNING: This disables YOUR user WinINET proxy settings.
echo          Use when the browser shows ERR_PROXY_CONNECTION_FAILED.
echo.
echo          For ongoing protection after relief:
echo            python -m src proxy-guardian --once
echo            python -m src install-guardian-task --confirm INSTALL_GUARDIAN_TASK --dry-run false
echo.
echo Press Ctrl+C to cancel, or
pause

"%PYTHON%" -m src proxy-fix --confirm DISABLE_WININET_PROXY --dry-run false
set "RC=%ERRORLEVEL%"

if %RC% neq 0 (
    echo.
    echo Python proxy-fix failed ^(exit %RC%^). Falling back to reg.exe...
    reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyEnable /t REG_DWORD /d 0 /f
    reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyServer /f >nul 2>&1
)

echo.
echo Restart your browser or open a new window.
echo Audit: logs\proxy_guardian.jsonl and governed proxy-fix output above.
echo.
pause
popd
endlocal
