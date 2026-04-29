@echo off
setlocal EnableExtensions

REM Windows Network Recovery Toolkit
REM Guided repair script. It diagnoses first, then asks before changing anything.

title Windows Network Recovery Toolkit - Automatic Guided Fix

set "SCRIPT_DIR=%~dp0"
set "ROOT_DIR=%SCRIPT_DIR%.."
set "RESULT_FILE=%ROOT_DIR%\logs\last_diagnosis_result.txt"
set "ISSUE_CODE=UNKNOWN"
set "ISSUE_NAME=Unknown / needs manual review"
set "RECOMMENDATION=Review the diagnosis log manually."
set "REPAIR_SCRIPT="
set "REPAIR_NAME="
set "RESTART_REQUIRED=NO"

echo ============================================================
echo  Windows Network Recovery Toolkit - Automatic Guided Fix
echo ============================================================
echo.
echo This script will run automatic diagnosis first.
echo It will ask before applying any repair.
echo.

REM Check for Administrator permission.
net session >nul 2>&1
if not "%errorlevel%"=="0" (
    echo [ERROR] This script must be run as Administrator.
    echo.
    echo Right-click auto_fix.bat and select "Run as administrator".
    echo.
    pause
    exit /b 1
)

echo [OK] Administrator permission confirmed.
echo.

call "%SCRIPT_DIR%auto_diagnose.bat" --no-pause
if not "%errorlevel%"=="0" (
    echo.
    echo [ERROR] Diagnosis failed. No repair was applied.
    echo.
    pause
    exit /b 1
)

if not exist "%RESULT_FILE%" (
    echo.
    echo [ERROR] Diagnosis result file was not found.
    echo No repair was applied.
    echo.
    pause
    exit /b 1
)

for /f "usebackq tokens=1,* delims==" %%A in ("%RESULT_FILE%") do (
    if /i "%%A"=="ISSUE_CODE" set "ISSUE_CODE=%%B"
    if /i "%%A"=="ISSUE_NAME" set "ISSUE_NAME=%%B"
    if /i "%%A"=="RECOMMENDATION" set "RECOMMENDATION=%%B"
)

echo ============================================================
echo  Guided Repair Recommendation
echo ============================================================
echo.
echo Likely problem: %ISSUE_NAME%
echo Recommendation: %RECOMMENDATION%
echo.

if /i "%ISSUE_CODE%"=="DNS" (
    set "REPAIR_SCRIPT=%SCRIPT_DIR%reset_dns.bat"
    set "REPAIR_NAME=reset_dns.bat"
)

if /i "%ISSUE_CODE%"=="PROXY" (
    set "REPAIR_SCRIPT=%SCRIPT_DIR%reset_proxy.bat"
    set "REPAIR_NAME=reset_proxy.bat"
)

if /i "%ISSUE_CODE%"=="STACK" (
    set "REPAIR_SCRIPT=%SCRIPT_DIR%one_click_fix.bat"
    set "REPAIR_NAME=one_click_fix.bat"
    set "RESTART_REQUIRED=YES"
)

if /i "%ISSUE_CODE%"=="UNKNOWN" (
    set "REPAIR_SCRIPT=%SCRIPT_DIR%one_click_fix.bat"
    set "REPAIR_NAME=one_click_fix.bat"
    set "RESTART_REQUIRED=YES"
)

if /i "%ISSUE_CODE%"=="HTTPS" (
    set "REPAIR_SCRIPT=%SCRIPT_DIR%one_click_fix.bat"
    set "REPAIR_NAME=one_click_fix.bat"
    set "RESTART_REQUIRED=YES"
    echo Note: HTTPS problems can also be caused by VPN, antivirus, proxy inspection, or firewall software.
    echo The full repair is offered as a fallback, but it may not fix third-party software issues.
    echo.
)

if /i "%ISSUE_CODE%"=="BROWSER" (
    echo No automatic repair is recommended because the main network tests passed.
    echo Try another browser, clear browser proxy settings, or reset Edge settings.
    echo.
    echo reset_firewall.bat will not be run automatically.
    echo.
    pause
    exit /b 0
)

if "%REPAIR_SCRIPT%"=="" (
    echo No automatic repair mapping is available for this diagnosis.
    echo Check VPN / antivirus / firewall software and review the log manually.
    echo.
    pause
    exit /b 0
)

echo WARNING:
echo The next step will run %REPAIR_NAME%.
echo This will modify Windows network settings.
echo reset_firewall.bat is never run automatically by this script.
echo.

set /p CONFIRM=Type YES to apply this repair now: 
if /i not "%CONFIRM%"=="YES" (
    echo.
    echo Repair cancelled. No changes were applied by auto_fix.bat.
    echo.
    pause
    exit /b 0
)

echo.
echo Running %REPAIR_NAME%...
echo.
call "%REPAIR_SCRIPT%"

echo.
echo ============================================================
echo  Guided repair finished
echo ============================================================
echo.

if /i "%RESTART_REQUIRED%"=="YES" (
    echo IMPORTANT: Restart Windows before testing the network again.
    echo Winsock and TCP/IP resets do not fully apply until reboot.
    echo.
)

echo If the issue remains, check VPN, antivirus, firewall software, router, or ISP connectivity.
echo.

pause
endlocal
