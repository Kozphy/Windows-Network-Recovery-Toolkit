@echo off
setlocal

REM Windows Network Recovery Toolkit
REM Diagnostic script for common Windows network, DNS, curl, and proxy issues.
REM --
REM Purpose: Read-only checks (prints status only per echo labels below).
REM Privileges: Standard user unless a probe requires elevation in your environment.
REM Side effects: None beyond console output and transient outbound probes.

title Windows Network Recovery Toolkit - Network Check

echo ============================================================
echo  Windows Network Recovery Toolkit - Network Check
echo ============================================================
echo.
echo This script does not change network settings.
echo It only runs checks and prints diagnostic information.
echo.

echo [1/5] Testing direct internet reachability with ping...
ping -n 2 8.8.8.8 >nul
if "%errorlevel%"=="0" (
    echo [OK] Ping to 8.8.8.8 succeeded.
    set "PING_STATUS=OK"
) else (
    echo [FAIL] Ping to 8.8.8.8 failed.
    set "PING_STATUS=FAIL"
)
echo.

echo [2/5] Testing DNS lookup with nslookup...
nslookup google.com >nul 2>&1
if "%errorlevel%"=="0" (
    echo [OK] DNS lookup for google.com succeeded.
    set "DNS_STATUS=OK"
) else (
    echo [FAIL] DNS lookup for google.com failed.
    set "DNS_STATUS=FAIL"
)
echo.

echo [3/5] Testing HTTP request with curl...
curl.exe -I --max-time 10 http://example.com >nul 2>&1
if "%errorlevel%"=="0" (
    echo [OK] curl reached http://example.com.
    set "CURL_STATUS=OK"
) else (
    echo [FAIL] curl could not reach http://example.com.
    set "CURL_STATUS=FAIL"
)
echo.

echo [4/5] Current WinHTTP proxy settings:
netsh winhttp show proxy
echo.

echo [5/5] Current user proxy registry values:
reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyEnable 2>nul
reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyServer 2>nul
reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v AutoConfigURL 2>nul
echo.

echo ============================================================
echo  Readable Diagnosis
echo ============================================================
echo.

if "%PING_STATUS%"=="FAIL" (
    echo - Ping failed. Check Wi-Fi/Ethernet connection, router, adapter status, or ISP connectivity.
) else (
    echo - Ping works. Basic internet reachability appears available.
)

if "%DNS_STATUS%"=="FAIL" (
    echo - DNS lookup failed. Try reset_dns.bat or check DNS server settings.
) else (
    echo - DNS lookup works. Domain names can resolve.
)

if "%CURL_STATUS%"=="FAIL" (
    echo - curl failed. If ping and DNS worked, check proxy, firewall, VPN, or Winsock settings.
) else (
    echo - curl works. HTTP connectivity appears available.
)

echo.
echo Suggested next steps:
echo - If proxy values are set and you do not use a proxy, run reset_proxy.bat.
echo - If DNS failed, run reset_dns.bat.
echo - If ping works but curl or browsers fail, run one_click_fix.bat as Administrator.
echo.

pause
endlocal
