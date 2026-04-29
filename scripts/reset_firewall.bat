@echo off
setlocal

REM Windows Network Recovery Toolkit
REM Firewall reset script. This restores Windows Firewall rules to defaults.

title Windows Network Recovery Toolkit - Reset Firewall

echo ============================================================
echo  Windows Network Recovery Toolkit - Reset Firewall
echo ============================================================
echo.
echo WARNING:
echo This will reset Windows Firewall rules to their default state.
echo Custom allow/block rules created by apps, games, VPNs, or administrators may be removed.
echo.
echo Use this only when firewall rules appear broken or network apps are blocked unexpectedly.
echo.

REM Check for Administrator permission.
net session >nul 2>&1
if not "%errorlevel%"=="0" (
    echo [ERROR] This script must be run as Administrator.
    echo.
    echo Right-click reset_firewall.bat and select "Run as administrator".
    echo.
    pause
    exit /b 1
)

set /p CONFIRM=Type YES to reset Windows Firewall rules: 
if /i not "%CONFIRM%"=="YES" (
    echo Firewall reset cancelled.
    echo.
    pause
    exit /b 0
)

echo.
echo Resetting Windows Firewall to default policy...
netsh advfirewall reset
echo.

echo Firewall reset completed.
echo Restart affected apps and test the network again.
echo.

pause
endlocal
