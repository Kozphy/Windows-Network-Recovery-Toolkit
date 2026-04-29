@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM Windows Network Recovery Toolkit
REM Read-only static scan for possible connection leak patterns in code.

title Windows Network Recovery Toolkit - Code Leak Pattern Detection

set "SUPPRESS_PAUSE=NO"
if /i "%~1"=="--no-pause" set "SUPPRESS_PAUSE=YES"

set "TMP_MATCH=%TEMP%\wnrt_code_leak_matches_%RANDOM%%RANDOM%.txt"
set "TMP_MATCH_JS=%TEMP%\wnrt_code_leak_matches_js_%RANDOM%%RANDOM%.txt"
set /a RISKY_FILES=0
set /a RISKY_MATCHES=0

echo ==========================================
echo Code Leak Pattern Detection
echo ==========================================
echo.
echo Scope: scanning current project folder recursively.
echo This script is read-only. It does not modify files.
echo.
echo Detected risky patterns:

for /r %%F in (*.py) do call :scan_python "%%~fF"
for /r %%F in (*.js *.jsx *.ts *.tsx *.mjs *.cjs) do call :scan_js "%%~fF"

if !RISKY_FILES! EQU 0 (
    echo None detected with current heuristic rules.
)

echo.
echo ------------------------------------------
if !RISKY_FILES! GTR 0 (
    echo Diagnosis:
    echo Possible connection leak pattern
    echo.
    echo Why:
    echo - Frequent direct HTTP calls found without clear reuse/pooling signal.
    echo - Each new request can create extra TCP connection churn under load.
    echo.
    echo Suggested fix:
    echo - Python: use requests.Session^(^) and reuse session.get/session.post.
    echo - Node/JS: reuse axios instance, keepAlive agent, or connection pool.
    echo - Re-run monitor_connections.bat to verify connection trends improve.
) else (
    echo Diagnosis:
    echo No obvious leak pattern detected by this heuristic scan.
    echo.
    echo Suggested next step:
    echo - If runtime spikes still happen, use monitor_connections.bat and check_connection_exhaustion.bat.
)

set "TOP_PID=0"
set "TOP_NAME=Unknown"
set "TOP_CONN=0"
for /f "tokens=1-3 delims=|" %%A in ('powershell -NoProfile -ExecutionPolicy Bypass -Command "$top = Get-NetTCPConnection | Group-Object OwningProcess | Sort-Object Count -Descending | Select-Object -First 1; if ($top) { $procId=[int]$top.Name; $name='Unknown'; try { $name=(Get-Process -Id $procId -ErrorAction Stop).ProcessName } catch {} ; '{0}|{1}|{2}' -f $procId, $name, $top.Count } else { '0|None|0' }"') do (
    set "TOP_PID=%%A"
    set "TOP_NAME=%%B"
    set "TOP_CONN=%%C"
)

echo !TOP_CONN! | findstr /r "^[0-9][0-9]*$" >nul 2>&1
if not errorlevel 1 if !TOP_CONN! GTR 500 (
    echo.
    echo Bonus hint:
    echo High live connection process detected: PID !TOP_PID!, connections !TOP_CONN!.
    echo If this process maps to your code, scan that project folder first.
)

echo ------------------------------------------
echo.
echo Scan completed.
echo.

if exist "%TMP_MATCH%" del "%TMP_MATCH%" >nul 2>&1
if exist "%TMP_MATCH_JS%" del "%TMP_MATCH_JS%" >nul 2>&1
if /i not "%SUPPRESS_PAUSE%"=="YES" pause
endlocal
exit /b 0

:should_skip
set "SCAN_FILE=%~1"
if /i not "!SCAN_FILE:\node_modules\=!"=="!SCAN_FILE!" exit /b 0
if /i not "!SCAN_FILE:\.git\=!"=="!SCAN_FILE!" exit /b 0
if /i not "!SCAN_FILE:\logs\=!"=="!SCAN_FILE!" exit /b 0
exit /b 1

:scan_python
set "FILE=%~1"
call :should_skip "%FILE%"
if "%errorlevel%"=="0" exit /b 0

findstr /n /i /c:"requests.get(" /c:"requests.post(" /c:"requests.put(" /c:"requests.delete(" /c:"requests.head(" /c:"requests.patch(" "%FILE%" >"%TMP_MATCH%" 2>nul
if errorlevel 1 exit /b 0

findstr /i /c:"requests.Session(" "%FILE%" >nul 2>&1
if not errorlevel 1 exit /b 0

set /a RISKY_FILES+=1
set /a SHOWN=0
echo.
set "RELFILE=%FILE:%CD%\=%"
echo File: !RELFILE!

for /f "usebackq delims=" %%L in ("%TMP_MATCH%") do (
    set /a SHOWN+=1
    set /a RISKY_MATCHES+=1
    if !SHOWN! LEQ 5 (
        for /f "tokens=1,* delims=:" %%a in ("%%L") do (
            echo Line %%a:
            echo %%b
            echo -^> No session reuse detected
            echo.
        )
    )
)
exit /b 0

:scan_js
set "FILE=%~1"
call :should_skip "%FILE%"
if "%errorlevel%"=="0" exit /b 0

findstr /n /i /c:"fetch(" /c:"axios(" /c:"axios.get(" /c:"axios.post(" /c:"axios.request(" "%FILE%" >"%TMP_MATCH_JS%" 2>nul
if errorlevel 1 exit /b 0

findstr /i /c:"axios.create(" /c:"keepAlive: true" /c:"new Agent(" /c:"new Pool(" /c:"undici.Pool" /c:"undici.Agent" "%FILE%" >nul 2>&1
if not errorlevel 1 exit /b 0

set /a RISKY_FILES+=1
set /a SHOWN=0
echo.
set "RELFILE=%FILE:%CD%\=%"
echo File: !RELFILE!

for /f "usebackq delims=" %%L in ("%TMP_MATCH_JS%") do (
    set /a SHOWN+=1
    set /a RISKY_MATCHES+=1
    if !SHOWN! LEQ 5 (
        for /f "tokens=1,* delims=:" %%a in ("%%L") do (
            echo Line %%a:
            echo %%b
            echo -^> No pooling/reuse signal detected
            echo.
        )
    )
)
exit /b 0
