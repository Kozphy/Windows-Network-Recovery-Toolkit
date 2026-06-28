@echo off
setlocal
REM ============================================================
REM WNRT Emergency WinINET Proxy Reset (HKCU)
REM Purpose:     Immediate browser relief when ERR_PROXY_CONNECTION_FAILED
REM Privileges:  Current user (HKCU Internet Settings)
REM Inputs:      Interactive pause before apply
REM Outputs:     reg.exe success/failure messages
REM Side effects: ProxyEnable=0; deletes ProxyServer value if present
REM Safety:      Does NOT diagnose root cause; does not change WinHTTP or Cursor settings
REM Idempotency: Safe to rerun when proxy already disabled
REM Recovery:    Re-enable proxy manually or via corporate tooling if required
REM Example:     Double-click or: scripts\fix-wininet-proxy.cmd
REM Audit:        No JSONL audit — use proxy-disable CLI for governed apply
REM ============================================================
title WNRT Emergency WinINET Proxy Reset

echo.
echo ============================================================
echo   EMERGENCY: Disable current-user WinINET proxy (HKCU)
echo ============================================================
echo.
echo WARNING: This manually disables YOUR user proxy settings.
echo          Use only when the browser shows ERR_PROXY_CONNECTION_FAILED
echo          or similar proxy errors and you need immediate relief.
echo.
echo          This does NOT diagnose root cause. For ongoing protection:
echo            scripts\configure-cursor-no-proxy.ps1
echo            scripts\install-dead-proxy-guardian.ps1
echo.
echo Press Ctrl+C to cancel, or
pause

reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyEnable /t REG_DWORD /d 0 /f
if errorlevel 1 (
    echo ERROR: Failed to set ProxyEnable=0
    goto :done
)
echo OK: ProxyEnable set to 0

reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyServer /f >nul 2>&1
if errorlevel 1 (
    echo OK: ProxyServer was not set or already removed
) else (
    echo OK: ProxyServer removed
)

echo.
echo WinINET proxy disabled for current user.
echo Restart your browser or open a new window.
echo.

:done
pause
endlocal
