@echo off
setlocal

REM Windows Network Recovery Toolkit
REM Full repair script for common Windows network stack, DNS, and proxy issues.

title Windows Network Recovery Toolkit - One Click Fix

echo ============================================================
echo  Windows Network Recovery Toolkit - One Click Fix
echo ============================================================
echo.

REM Check for Administrator permission.
net session >nul 2>&1
if not "%errorlevel%"=="0" (
    echo [ERROR] This script must be run as Administrator.
    echo.
    echo Right-click one_click_fix.bat and select "Run as administrator".
    echo.
    pause
    exit /b 1
)

echo [OK] Administrator permission confirmed.
echo.

echo [1/6] Resetting Winsock catalog...
netsh winsock reset
echo.

echo [2/6] Resetting TCP/IP stack...
netsh int ip reset
echo.

echo [3/6] Flushing DNS resolver cache...
ipconfig /flushdns
echo.

echo [4/6] Resetting WinHTTP proxy...
netsh winhttp reset proxy
echo.

echo [5/6] Disabling user-level proxy setting...
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyEnable /t REG_DWORD /d 0 /f
echo.

echo [6/6] Removing user-level proxy server and auto-config values if present...
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyServer /f >nul 2>&1
if "%errorlevel%"=="0" (
    echo [OK] Removed ProxyServer.
) else (
    echo [INFO] ProxyServer was not set.
)

reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v AutoConfigURL /f >nul 2>&1
if "%errorlevel%"=="0" (
    echo [OK] Removed AutoConfigURL.
) else (
    echo [INFO] AutoConfigURL was not set.
)

echo.
echo ============================================================
echo  Repair steps completed.
echo ============================================================
echo.
echo IMPORTANT: Restart Windows before testing the network again.
echo.
echo After restarting, try:
echo - Opening a website in your browser
echo - Running: ping 8.8.8.8
echo - Running: nslookup google.com
echo - Running: curl http://example.com
echo.

pause
endlocal
