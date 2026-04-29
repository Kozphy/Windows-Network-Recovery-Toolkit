@echo off
setlocal EnableExtensions

REM Windows Network Recovery Toolkit
REM Read-only automatic diagnosis script with beginner-friendly recommendations.

title Windows Network Recovery Toolkit - Automatic Diagnosis

set "SCRIPT_DIR=%~dp0"
set "ROOT_DIR=%SCRIPT_DIR%.."
set "LOG_DIR=%ROOT_DIR%\logs"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

for /f %%I in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "TS=%%I"
set "LOG_FILE=%LOG_DIR%\network_diagnosis_%TS%.txt"
set "RESULT_FILE=%LOG_DIR%\last_diagnosis_result.txt"
set "TEMP_FILE=%TEMP%\wnrt_auto_diagnose_%RANDOM%.tmp"

set "PING_STATUS=UNKNOWN"
set "DNS_STATUS=UNKNOWN"
set "TCP443_STATUS=UNKNOWN"
set "HTTPS_STATUS=UNKNOWN"
set "PROXY_CONFIGURED=NO"
set "ISSUE_CODE=UNKNOWN"
set "ISSUE_NAME=Unknown / needs manual review"
set "RECOMMENDATION=Check VPN / antivirus / firewall software and review the log manually."

call :log "============================================================"
call :log " Windows Network Recovery Toolkit - Automatic Diagnosis"
call :log "============================================================"
call :log ""
call :log "Log file: %LOG_FILE%"
call :log ""

REM Check for Administrator permission.
net session >nul 2>&1
if not "%errorlevel%"=="0" (
    call :log "[ERROR] This script must be run as Administrator."
    call :log ""
    call :log "Right-click auto_diagnose.bat and select Run as administrator."
    goto :fail
)

call :log "[OK] Administrator permission confirmed."
call :log ""
call :log "This script is read-only. It does not change network settings."
call :log ""

call :log "[1/7] Current network adapters"
call :run "netsh interface show interface"

call :log "[2/7] Testing basic internet reachability with ping"
ping -n 2 8.8.8.8 >"%TEMP_FILE%" 2>&1
if "%errorlevel%"=="0" (
    set "PING_STATUS=OK"
) else (
    set "PING_STATUS=FAIL"
)
call :dump
call :log "Ping status: %PING_STATUS%"
call :log ""

call :log "[3/7] Testing DNS with nslookup google.com"
nslookup google.com >"%TEMP_FILE%" 2>&1
if "%errorlevel%"=="0" (
    set "DNS_STATUS=OK"
) else (
    set "DNS_STATUS=FAIL"
)
call :dump
call :log "DNS status: %DNS_STATUS%"
call :log ""

call :log "[4/7] Testing TCP 443 with PowerShell Test-NetConnection"
powershell -NoProfile -ExecutionPolicy Bypass -Command "Test-NetConnection google.com -Port 443 -InformationLevel Detailed" >"%TEMP_FILE%" 2>&1
findstr /i /c:"TcpTestSucceeded" "%TEMP_FILE%" | findstr /i "True" >nul 2>&1
if "%errorlevel%"=="0" (
    set "TCP443_STATUS=OK"
) else (
    set "TCP443_STATUS=FAIL"
)
call :dump
call :log "TCP 443 status: %TCP443_STATUS%"
call :log ""

call :log "[5/7] Testing HTTPS with curl"
curl.exe -I --max-time 10 https://www.google.com >"%TEMP_FILE%" 2>&1
if "%errorlevel%"=="0" (
    set "HTTPS_STATUS=OK"
) else (
    set "HTTPS_STATUS=FAIL"
)
call :dump
call :log "HTTPS status: %HTTPS_STATUS%"
call :log ""

call :log "[6/7] WinHTTP proxy settings"
netsh winhttp show proxy >"%TEMP_FILE%" 2>&1
findstr /i /c:"Direct access" "%TEMP_FILE%" >nul 2>&1
if not "%errorlevel%"=="0" set "PROXY_CONFIGURED=YES"
call :dump

call :log "[7/7] User proxy registry values"
reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyEnable >"%TEMP_FILE%" 2>&1
findstr /i "0x1" "%TEMP_FILE%" >nul 2>&1
if "%errorlevel%"=="0" set "PROXY_CONFIGURED=YES"
call :dump

reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v ProxyServer >"%TEMP_FILE%" 2>&1
if "%errorlevel%"=="0" set "PROXY_CONFIGURED=YES"
call :dump

reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v AutoConfigURL >"%TEMP_FILE%" 2>&1
if "%errorlevel%"=="0" set "PROXY_CONFIGURED=YES"
call :dump

reg query "HKCU\Software\Microsoft\Windows\CurrentVersion\Internet Settings" /v AutoDetect >"%TEMP_FILE%" 2>&1
call :dump
call :log "Proxy configured or suspected: %PROXY_CONFIGURED%"
call :log ""

call :classify

call :log "============================================================"
call :log " Diagnosis Summary"
call :log "============================================================"
call :log ""
call :log "Likely problem: %ISSUE_NAME%"
call :log "Recommendation: %RECOMMENDATION%"
call :log ""
call :log "Saved full diagnostic log to:"
call :log "%LOG_FILE%"
call :log ""
call :log "Running rule-based root cause classifier..."
call :log ""

echo.
echo ============================================================
echo  Root Cause Classifier (additional read-only analysis)
echo ============================================================
echo.
call "%SCRIPT_DIR%classify_root_cause.bat" --no-pause
echo.

(
    echo ISSUE_CODE=%ISSUE_CODE%
    echo ISSUE_NAME=%ISSUE_NAME%
    echo RECOMMENDATION=%RECOMMENDATION%
    echo LOG_FILE=%LOG_FILE%
) >"%RESULT_FILE%"

goto :success

:fail
if exist "%TEMP_FILE%" del "%TEMP_FILE%" >nul 2>&1
if /i not "%~1"=="--no-pause" pause
endlocal
exit /b 1

:success
if exist "%TEMP_FILE%" del "%TEMP_FILE%" >nul 2>&1
if /i not "%~1"=="--no-pause" pause
endlocal
exit /b 0

:classify
if "%DNS_STATUS%"=="FAIL" (
    set "ISSUE_CODE=DNS"
    set "ISSUE_NAME=DNS problem"
    set "RECOMMENDATION=Run reset_dns.bat."
    exit /b
)

if "%PROXY_CONFIGURED%"=="YES" if "%HTTPS_STATUS%"=="FAIL" (
    set "ISSUE_CODE=PROXY"
    set "ISSUE_NAME=Proxy problem"
    set "RECOMMENDATION=Run reset_proxy.bat."
    exit /b
)

if "%TCP443_STATUS%"=="FAIL" (
    set "ISSUE_CODE=STACK"
    set "ISSUE_NAME=TCP/IP or Winsock problem"
    set "RECOMMENDATION=Run one_click_fix.bat and restart."
    exit /b
)

if "%HTTPS_STATUS%"=="FAIL" (
    set "ISSUE_CODE=HTTPS"
    set "ISSUE_NAME=HTTPS/TLS/application-layer problem"
    set "RECOMMENDATION=Check VPN / antivirus / firewall software. If unsure, run one_click_fix.bat and restart."
    exit /b
)

if "%PING_STATUS%"=="OK" if "%DNS_STATUS%"=="OK" if "%TCP443_STATUS%"=="OK" if "%HTTPS_STATUS%"=="OK" (
    set "ISSUE_CODE=BROWSER"
    set "ISSUE_NAME=Browser-specific problem"
    set "RECOMMENDATION=Try another browser or reset Edge settings. If failures happen after the system has been running for a while, run check_connection_exhaustion.bat."
    exit /b
)

set "ISSUE_CODE=UNKNOWN"
set "ISSUE_NAME=Unknown / needs manual review"
set "RECOMMENDATION=Check VPN / antivirus / firewall software and review the log manually."
exit /b

:run
%~1 >"%TEMP_FILE%" 2>&1
call :dump
exit /b

:dump
type "%TEMP_FILE%"
type "%TEMP_FILE%" >>"%LOG_FILE%"
echo.
echo.>>"%LOG_FILE%"
exit /b

:log
if "%~1"=="" (
    echo.
    echo.>>"%LOG_FILE%"
) else (
    echo %~1
    echo %~1>>"%LOG_FILE%"
)
exit /b
