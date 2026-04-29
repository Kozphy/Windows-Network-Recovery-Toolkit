@echo off
setlocal EnableExtensions

REM Windows Network Recovery Toolkit
REM Read-only recommendation engine for safest next fix action.

title Windows Network Recovery Toolkit - Fix Recommendation Engine

set "SUPPRESS_PAUSE=NO"
if /i "%~1"=="--no-pause" set "SUPPRESS_PAUSE=YES"

set "PING_STATUS=UNKNOWN"
set "DNS_STATUS=UNKNOWN"
set "HTTPS_STATUS=UNKNOWN"
set "PROXY_ENABLED=NO"
set "TIME_WAIT_COUNT=0"

set "DETECTED_ISSUE=Unknown / needs manual review"
set "RECOMMENDED_FIX=Run auto_diagnose.bat again and review details."
set "RISK_LEVEL=LOW"
set "WHY_TEXT=Signals were mixed and no single dominant pattern was detected."
set "NEXT_STEP=Retest on another network and check VPN/antivirus/firewall software."

echo ==========================================
echo Fix Recommendation Engine
echo ==========================================
echo.
echo This engine is advisory only.
echo It does NOT execute any fixes automatically.
echo.

echo [1/5] Checking ping reachability...
ping -n 2 8.8.8.8 >nul 2>&1
if "%errorlevel%"=="0" (
    set "PING_STATUS=OK"
) else (
    set "PING_STATUS=FAIL"
)

echo [2/5] Checking DNS resolution...
nslookup google.com >nul 2>&1
if "%errorlevel%"=="0" (
    set "DNS_STATUS=OK"
) else (
    set "DNS_STATUS=FAIL"
)

echo [3/5] Checking HTTPS connectivity...
curl.exe -I --max-time 10 https://www.google.com >nul 2>&1
if "%errorlevel%"=="0" (
    set "HTTPS_STATUS=OK"
) else (
    set "HTTPS_STATUS=FAIL"
)

echo [4/5] Checking proxy configuration...
netsh winhttp show proxy | findstr /i /c:"Direct access" >nul 2>&1
if not "%errorlevel%"=="0" set "PROXY_ENABLED=YES"
reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyEnable 2>nul | findstr /i "0x1" >nul 2>&1
if "%errorlevel%"=="0" set "PROXY_ENABLED=YES"
reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyServer >nul 2>&1
if "%errorlevel%"=="0" set "PROXY_ENABLED=YES"
reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v AutoConfigURL >nul 2>&1
if "%errorlevel%"=="0" set "PROXY_ENABLED=YES"

echo [5/5] Checking TIME_WAIT pressure...
for /f %%A in ('netstat -an ^| find "TIME_WAIT" /c') do set "TIME_WAIT_COUNT=%%A"

REM Priority-based recommendation rules (safest fix first).
if "%DNS_STATUS%"=="FAIL" (
    set "DETECTED_ISSUE=DNS resolution failure"
    set "RECOMMENDED_FIX=Run: reset_dns.bat"
    set "RISK_LEVEL=LOW"
    set "WHY_TEXT=DNS lookup failed while basic network path may still be reachable."
    set "NEXT_STEP=Run reset_dns.bat, then retry nslookup, curl, and browser access."
    goto :print
)

if "%PROXY_ENABLED%"=="YES" (
    set "DETECTED_ISSUE=Proxy configuration issue"
    set "RECOMMENDED_FIX=Run: reset_proxy.bat"
    set "RISK_LEVEL=LOW"
    set "WHY_TEXT=Proxy settings are enabled and can block normal browser/API traffic."
    set "NEXT_STEP=Run reset_proxy.bat, reopen browser, and retest."
    goto :print
)

if "%PING_STATUS%"=="OK" if "%DNS_STATUS%"=="OK" if "%HTTPS_STATUS%"=="FAIL" (
    set "DETECTED_ISSUE=HTTPS/TLS/firewall path issue"
    set "RECOMMENDED_FIX=Run: one_click_fix.bat"
    set "RISK_LEVEL=MEDIUM"
    set "WHY_TEXT=Ping and DNS work but HTTPS fails, suggesting stack/path filtering issues."
    set "NEXT_STEP=Run one_click_fix.bat, restart Windows, then retest."
    goto :print
)

if %TIME_WAIT_COUNT% GTR 5000 (
    set "DETECTED_ISSUE=Possible connection exhaustion"
    set "RECOMMENDED_FIX=Advisory: restart network-heavy apps and check for connection leaks"
    set "RISK_LEVEL=NONE (ADVISORY)"
    set "WHY_TEXT=TIME_WAIT is above 5000, which can indicate high socket churn or leak patterns."
    set "NEXT_STEP=Run check_connection_exhaustion.bat and detect_code_leak.bat, then optimize connection reuse."
    goto :print
)

if "%PING_STATUS%"=="FAIL" (
    set "DETECTED_ISSUE=Network unreachable"
    set "RECOMMENDED_FIX=Advisory: verify adapter/router/ISP path first"
    set "RISK_LEVEL=NONE (ADVISORY)"
    set "WHY_TEXT=Ping failed, so repair scripts are less useful before connectivity is restored."
    set "NEXT_STEP=Check Wi-Fi/Ethernet, router, and ISP status, then rerun diagnostics."
    goto :print
)

if not "%PING_STATUS%"=="OK" goto :fallback
if not "%DNS_STATUS%"=="OK" goto :fallback
if not "%HTTPS_STATUS%"=="OK" goto :fallback
if not "%PROXY_ENABLED%"=="NO" goto :fallback
if %TIME_WAIT_COUNT% LEQ 5000 (
    set "DETECTED_ISSUE=No critical issue from current snapshot"
    set "RECOMMENDED_FIX=Advisory: no immediate repair script recommended"
    set "RISK_LEVEL=NONE (ADVISORY)"
    set "WHY_TEXT=Core checks currently look healthy."
    set "NEXT_STEP=If failures are intermittent, run monitor_connections.bat and check_connection_exhaustion.bat during the issue."
    goto :print
)

:fallback
set "DETECTED_ISSUE=Inconsistent or mixed network state"
set "RECOMMENDED_FIX=Run: one_click_fix.bat"
set "RISK_LEVEL=MEDIUM-HIGH"
set "WHY_TEXT=Signals are inconsistent and targeted low-risk fixes were not enough to isolate root cause."
set "NEXT_STEP=Run one_click_fix.bat, restart Windows, then re-run diagnostics."

:print
echo.
echo ------------------------------------------
echo Detected issue:
echo %DETECTED_ISSUE%
echo.
echo Recommended fix:
echo ^> %RECOMMENDED_FIX%
echo.
echo Risk level:
echo %RISK_LEVEL%
echo.
echo Why:
echo %WHY_TEXT%
echo.
echo Next step:
echo %NEXT_STEP%
echo ------------------------------------------
echo.

if /i not "%SUPPRESS_PAUSE%"=="YES" pause
endlocal
exit /b 0
