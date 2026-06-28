@echo off
setlocal

REM Windows Network Recovery Toolkit — Reset DNS
REM Purpose:     Flush Windows DNS resolver cache; show adapter DNS summary
REM Privileges:  Administrator required (net session check)
REM Inputs:      Interactive — pauses before and after
REM Outputs:     ipconfig /flushdns result; filtered ipconfig /all DNS lines
REM Side effects: Clears local DNS cache only; does not change adapter DNS servers
REM Safety:      Does not modify firewall, proxy, or routing
REM Idempotency: Safe to rerun; cache flush is repeatable
REM Recovery:    If resolution still fails, check adapter DNS or use diagnose CLI
REM Example:     Right-click Run as administrator: scripts\reset_dns.bat
REM Note:        ChatGPT auto-fix may call ipconfig /flushdns without this bat (user scope)

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
