@echo off
setlocal EnableExtensions

REM Windows Network Recovery Toolkit
REM Read-only root cause classifier based on network diagnostics.
REM --
REM Purpose: Infer likely issue category from prior diagnostic variables/logs (no mutation).
REM Side effects: Console output only unless external callers chain this script.

title Windows Network Recovery Toolkit - Root Cause Classification

set "PING_STATUS=UNKNOWN"
set "DNS_STATUS=UNKNOWN"
set "HTTPS_STATUS=UNKNOWN"
set "PROXY_ENABLED=NO"
set "TIME_WAIT_COUNT=0"
set "ESTABLISHED_COUNT=0"
set "DIAGNOSIS=Unknown / needs manual review"
set "CONFIDENCE=Medium confidence"
set "WHY_1=Signals are mixed."
set "WHY_2=No single dominant failure pattern was detected."
set "ACTION_1=Run auto_diagnose.bat and review the full log."
set "ACTION_2=Try another network and retest."
set "ACTION_3=Check VPN, antivirus, and firewall software."

set "SUPPRESS_PAUSE=NO"
if /i "%~1"=="--no-pause" set "SUPPRESS_PAUSE=YES"

echo ==========================================
echo Root Cause Classification
echo ==========================================
echo.
echo This script is read-only. It does not modify system settings.
echo.

echo [1/5] Testing ping reachability...
ping -n 2 8.8.8.8 >nul 2>&1
if "%errorlevel%"=="0" (
    set "PING_STATUS=OK"
) else (
    set "PING_STATUS=FAIL"
)

echo [2/5] Testing DNS resolution...
nslookup google.com >nul 2>&1
if "%errorlevel%"=="0" (
    set "DNS_STATUS=OK"
) else (
    set "DNS_STATUS=FAIL"
)

echo [3/5] Testing HTTPS connectivity...
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

echo [5/5] Checking connection pressure...
for /f %%A in ('netstat -an ^| find "TIME_WAIT" /c') do set "TIME_WAIT_COUNT=%%A"
for /f %%A in ('netstat -an ^| find "ESTABLISHED" /c') do set "ESTABLISHED_COUNT=%%A"

REM Rule-based classification.
if "%PING_STATUS%"=="FAIL" (
    set "DIAGNOSIS=Network unreachable"
    set "CONFIDENCE=High confidence"
    set "WHY_1=Ping to 8.8.8.8 failed."
    set "WHY_2=The machine cannot reliably reach the internet path."
    set "ACTION_1=Check Wi-Fi/Ethernet link, adapter state, and router status."
    set "ACTION_2=Try another network (for example a mobile hotspot)."
    set "ACTION_3=If still failing, check ISP or local network outages."
    goto :print
)

if "%DNS_STATUS%"=="FAIL" (
    set "DIAGNOSIS=DNS issue"
    set "CONFIDENCE=High confidence"
    set "WHY_1=Ping works but DNS lookup failed."
    set "WHY_2=Name resolution is failing before traffic reaches websites."
    set "ACTION_1=Run reset_dns.bat."
    set "ACTION_2=Verify DNS server settings on the active adapter."
    set "ACTION_3=Retest with nslookup and browser access."
    goto :print
)

if "%PROXY_ENABLED%"=="YES" (
    set "DIAGNOSIS=Proxy misconfiguration"
    set "CONFIDENCE=High confidence"
    set "WHY_1=Proxy settings are enabled or detected."
    set "WHY_2=Proxy configuration often blocks browser and curl traffic when stale."
    set "ACTION_1=Run reset_proxy.bat."
    set "ACTION_2=Reopen browser and retest website access."
    set "ACTION_3=If proxy values return, check VPN or enterprise policy."
    goto :print
)

if "%HTTPS_STATUS%"=="FAIL" (
    set "DIAGNOSIS=HTTPS/TLS/firewall path issue"
    set "CONFIDENCE=Medium to high confidence"
    set "WHY_1=Ping and DNS work, but HTTPS test failed."
    set "WHY_2=Failure is likely in TLS, filtering, or application-layer network path."
    set "ACTION_1=Check VPN, antivirus web filtering, and firewall software."
    set "ACTION_2=Verify system date/time and try another network."
    set "ACTION_3=If unsure, run one_click_fix.bat and restart."
    goto :print
)

if %TIME_WAIT_COUNT% GTR 5000 (
    set "DIAGNOSIS=Connection exhaustion (possible socket leak)"
    set "CONFIDENCE=High confidence"
    set "WHY_1=HTTPS currently works, but TIME_WAIT is very high (greater than 5000)."
    set "WHY_2=High socket churn can consume ephemeral ports and cause failures over time."
    set "ACTION_1=Restart network-heavy applications first."
    set "ACTION_2=Review code for connection reuse (for example requests.Session)."
    set "ACTION_3=Restart Windows if ports appear exhausted now."
    goto :print
)

set "DIAGNOSIS=Possible router/NAT/session instability"
set "CONFIDENCE=Medium confidence"
set "WHY_1=Ping, DNS, HTTPS, and proxy checks look healthy at this moment."
set "WHY_2=Intermittent issues may still come from router NAT/session behavior or app-specific factors."
set "ACTION_1=If failures happen later, run check_connection_exhaustion.bat."
set "ACTION_2=Restart router/modem and monitor whether timeouts return."
set "ACTION_3=Test on another network to isolate local network behavior."

:print
echo.
echo Summary:
echo - Network (ping): %PING_STATUS%
echo - DNS (nslookup): %DNS_STATUS%
echo - HTTPS (curl): %HTTPS_STATUS%
echo - Proxy enabled: %PROXY_ENABLED%
echo - TIME_WAIT: %TIME_WAIT_COUNT%
echo - ESTABLISHED: %ESTABLISHED_COUNT%
echo.
echo ------------------------------------------
echo Diagnosis:
echo %CONFIDENCE%: %DIAGNOSIS%
echo.
echo Why:
echo - %WHY_1%
echo - %WHY_2%
echo.
echo Suggested actions:
echo - %ACTION_1%
echo - %ACTION_2%
echo - %ACTION_3%
echo ------------------------------------------
echo.

if /i not "%SUPPRESS_PAUSE%"=="YES" pause
endlocal
exit /b 0
