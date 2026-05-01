@echo off
setlocal

REM Windows Network Recovery Toolkit
REM DNS repair script for stale DNS cache or name resolution problems.
REM --
REM Purpose: Flush resolver cache / show DNS-facing config per script commands.
REM Privileges: Administrator required.
REM Side effects: ipconfig and related read-only/display steps as implemented below.
REM Idempotency: Safe to rerun; refreshes cache only.

title Windows Network Recovery Toolkit - Reset DNS

echo ============================================================
echo  Windows Network Recovery Toolkit - Reset DNS
echo ============================================================
echo.

REM Check for Administrator permission.
net session >nul 2>&1
if not "%errorlevel%"=="0" (
    echo [ERROR] This script must be run as Administrator.
    echo.
    echo Right-click reset_dns.bat and select "Run as administrator".
    echo.
    pause
    exit /b 1
)

echo [OK] Administrator permission confirmed.
echo.

echo [1/2] Flushing DNS resolver cache...
ipconfig /flushdns
echo.

echo [2/2] Showing current DNS configuration...
ipconfig /all | findstr /i "DNS Servers Connection-specific Suffix Description DHCP Enabled IPv4 Address"
echo.

echo DNS reset completed.
echo If DNS still fails, check adapter DNS settings or try a different DNS provider.
echo.

pause
endlocal
