@echo off
setlocal

REM Windows Network Recovery Toolkit
REM Proxy-only repair script for broken WinHTTP or user-level proxy settings.
REM --
REM Purpose: Clear WinHTTP proxy and HKCU proxy toggles consistent with toolkit policy.
REM Privileges: Administrator required.
REM Side effects: Mutates proxy configuration; Managed environments may revert via GPO.

title Windows Network Recovery Toolkit - Reset Proxy

echo ============================================================
echo  Windows Network Recovery Toolkit - Reset Proxy
echo ============================================================
echo.

REM Check for Administrator permission.
net session >nul 2>&1
if not "%errorlevel%"=="0" (
    echo [ERROR] This script must be run as Administrator.
    echo.
    echo Right-click reset_proxy.bat and select "Run as administrator".
    echo.
    pause
    exit /b 1
)

echo [OK] Administrator permission confirmed.
echo.

echo [1/4] Resetting WinHTTP proxy...
netsh winhttp reset proxy
echo.

echo [2/4] Disabling user-level proxy setting...
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyEnable /t REG_DWORD /d 0 /f
echo.

echo [3/4] Removing ProxyServer if present...
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyServer /f >nul 2>&1
if "%errorlevel%"=="0" (
    echo [OK] Removed ProxyServer.
) else (
    echo [INFO] ProxyServer was not set.
)
echo.

echo [4/4] Removing AutoConfigURL if present...
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v AutoConfigURL /f >nul 2>&1
if "%errorlevel%"=="0" (
    echo [OK] Removed AutoConfigURL.
) else (
    echo [INFO] AutoConfigURL was not set.
)
echo.

echo Current WinHTTP proxy settings:
netsh winhttp show proxy
echo.

echo Current user proxy values:
reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyEnable 2>nul
reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyServer 2>nul
reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v AutoConfigURL 2>nul
echo.

echo Proxy reset completed.
echo Restart browsers before testing again.
echo.

pause
endlocal
