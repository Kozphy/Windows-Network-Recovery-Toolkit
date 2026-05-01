@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM Windows Network Recovery Toolkit
REM Read-only real-time TCP connection monitor.
REM --
REM Purpose: Looping netstat-derived view; optional args set interval/iteration caps.
REM Side effects: Repeated read-only probes; Ctrl+C stops.

title Windows Network Recovery Toolkit - Live Connection Monitor

set "INTERVAL_SECONDS=3"
if not "%~1"=="" set "INTERVAL_SECONDS=%~1"
if defined MONITOR_INTERVAL_SECONDS set "INTERVAL_SECONDS=%MONITOR_INTERVAL_SECONDS%"
if not "%~2"=="" set "MAX_ITERATIONS=%~2"

set "ITERATION=0"
set "H_TW_1=-"
set "H_TW_2=-"
set "H_TW_3=-"
set "H_EST_1=-"
set "H_EST_2=-"
set "H_EST_3=-"
set "PREV_TIME_WAIT="
set "PREV_ESTABLISHED="
set "PREV_TOP_PID="
set "PREV_TOP_COUNT=0"

:loop
set /a ITERATION+=1

for /f %%A in ('netstat -an ^| find "TIME_WAIT" /c') do set "CUR_TIME_WAIT=%%A"
for /f %%A in ('netstat -an ^| find "ESTABLISHED" /c') do set "CUR_ESTABLISHED=%%A"

set "TOP_PID=0"
set "TOP_NAME=Unknown"
set "TOP_COUNT=0"
set "TOTAL_TCP=0"
for /f "tokens=1-4 delims=|" %%A in ('powershell -NoProfile -ExecutionPolicy Bypass -Command "$all = Get-NetTCPConnection; $total = $all.Count; $row = $all | Group-Object OwningProcess | Sort-Object Count -Descending | Select-Object -First 1 @{Name='PID';Expression={[int]$_.Name}}, @{Name='ProcessName';Expression={try { (Get-Process -Id ([int]$_.Name) -ErrorAction Stop).ProcessName } catch { 'Unknown' }}}, @{Name='Connections';Expression={$_.Count}}; if ($row) { '{0}|{1}|{2}|{3}' -f $row.PID, $row.ProcessName, $row.Connections, $total } else { '0|None|0|0' }"') do (
    set "TOP_PID=%%A"
    set "TOP_NAME=%%B"
    set "TOP_COUNT=%%C"
    set "TOTAL_TCP=%%D"
)

set "WARN_SPIKE=NO"
set "WARN_GROWTH=NO"
set "WARN_DOMINANT=NO"
set "WARN_TOP_INCREASING=NO"

if defined PREV_TIME_WAIT (
    set /a DELTA_TIME_WAIT=!CUR_TIME_WAIT!-!PREV_TIME_WAIT!
    if !DELTA_TIME_WAIT! GTR 500 set "WARN_SPIKE=YES"
    if !PREV_TIME_WAIT! GTR 0 (
        set /a DOUBLE_PREV_TW=!PREV_TIME_WAIT!*2
        if !CUR_TIME_WAIT! GTR !DOUBLE_PREV_TW! if !CUR_TIME_WAIT! GTR 1000 set "WARN_GROWTH=YES"
    )
) else (
    set "DELTA_TIME_WAIT=0"
)

if defined PREV_ESTABLISHED (
    set /a DELTA_ESTABLISHED=!CUR_ESTABLISHED!-!PREV_ESTABLISHED!
) else (
    set "DELTA_ESTABLISHED=0"
)

set "DENOM_TOTAL=!TOTAL_TCP!"
if !DENOM_TOTAL! LEQ 0 set "DENOM_TOTAL=1"
set /a TOP_RATIO=(!TOP_COUNT!*100)/!DENOM_TOTAL!
if !TOTAL_TCP! GEQ 20 if !TOP_RATIO! GEQ 70 set "WARN_DOMINANT=YES"

if defined PREV_TOP_PID (
    if "!TOP_PID!"=="!PREV_TOP_PID!" (
        set /a DELTA_TOP_COUNT=!TOP_COUNT!-!PREV_TOP_COUNT!
        if !DELTA_TOP_COUNT! GTR 100 set "WARN_TOP_INCREASING=YES"
    )
)

set "H_TW_1=!H_TW_2!"
set "H_TW_2=!H_TW_3!"
set "H_TW_3=!CUR_TIME_WAIT!"
set "H_EST_1=!H_EST_2!"
set "H_EST_2=!H_EST_3!"
set "H_EST_3=!CUR_ESTABLISHED!"

set "STATUS=Stable"
set "STATUS_LINE=No large spike detected in this sampling window."
set "CAUSE_1=Normal network usage."
set "CAUSE_2=Short-lived connections are within expected range."
set "CAUSE_3=Continue monitoring if failures are intermittent."
set /a WARN_COUNT=0
set "WARN_DETAILS="

if "%WARN_SPIKE%"=="YES" (
    set /a WARN_COUNT+=1
    if defined WARN_DETAILS (
        set "WARN_DETAILS=!WARN_DETAILS!; TIME_WAIT rapid spike"
    ) else (
        set "WARN_DETAILS=TIME_WAIT rapid spike"
    )
)

if "%WARN_GROWTH%"=="YES" (
    set /a WARN_COUNT+=1
    if defined WARN_DETAILS (
        set "WARN_DETAILS=!WARN_DETAILS!; TIME_WAIT abnormal growth"
    ) else (
        set "WARN_DETAILS=TIME_WAIT abnormal growth"
    )
)

if "%WARN_DOMINANT%"=="YES" (
    set /a WARN_COUNT+=1
    if defined WARN_DETAILS (
        set "WARN_DETAILS=!WARN_DETAILS!; dominant process !TOP_NAME! (PID !TOP_PID!)"
    ) else (
        set "WARN_DETAILS=dominant process !TOP_NAME! (PID !TOP_PID!)"
    )
)

if "%WARN_TOP_INCREASING%"=="YES" (
    set /a WARN_COUNT+=1
    if defined WARN_DETAILS (
        set "WARN_DETAILS=!WARN_DETAILS!; dominant process connection count increasing"
    ) else (
        set "WARN_DETAILS=dominant process connection count increasing"
    )
)

if !WARN_COUNT! GTR 0 (
    if !WARN_COUNT! EQU 1 (
        set "STATUS=[WARN] Connection anomaly detected"
        set "STATUS_LINE=Triggered signal: !WARN_DETAILS!."
    ) else (
        set "STATUS=[WARN] Multiple anomalies detected"
        set "STATUS_LINE=Triggered signals: !WARN_DETAILS!."
    )
    set "CAUSE_1=Connection behavior shows warning patterns that may share a root cause."
    set "CAUSE_2=Review all triggered signals together before choosing a mitigation."
    set "CAUSE_3=Check retry loops, socket reuse, and dominant-process behavior."
)

for /f %%A in ('powershell -NoProfile -Command "Get-Date -Format \"yyyy-MM-dd HH:mm:ss\""') do set "NOW_TS=%%A"

cls
echo ==========================================
echo Live Connection Monitor
echo ==========================================
echo Timestamp: !NOW_TS!   ^|   Interval: !INTERVAL_SECONDS!s   ^|   Iteration: !ITERATION!
echo.
echo TIME_WAIT:       !H_TW_1! ^> !H_TW_2! ^> !H_TW_3!   ^(delta !DELTA_TIME_WAIT!^)
echo ESTABLISHED:     !H_EST_1! ^> !H_EST_2! ^> !H_EST_3!   ^(delta !DELTA_ESTABLISHED!^)
echo Total TCP:       !TOTAL_TCP!
echo Top process:     !TOP_NAME! ^(PID !TOP_PID!^)   connections: !TOP_COUNT!   ratio: !TOP_RATIO!%%
echo.
echo ------------------------------------------
echo Status:
echo !STATUS!
echo !STATUS_LINE!
echo.
echo Possible causes:
echo - !CAUSE_1!
echo - !CAUSE_2!
echo - !CAUSE_3!
echo.
echo Tips:
echo - Press Ctrl+C to exit.
echo - Run check_connection_exhaustion.bat for one-time deep analysis.
echo ------------------------------------------

set "PREV_TIME_WAIT=!CUR_TIME_WAIT!"
set "PREV_ESTABLISHED=!CUR_ESTABLISHED!"
set "PREV_TOP_PID=!TOP_PID!"
set "PREV_TOP_COUNT=!TOP_COUNT!"

if defined MAX_ITERATIONS (
    if !ITERATION! GEQ !MAX_ITERATIONS! goto :done
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Sleep -Seconds !INTERVAL_SECONDS!" >nul 2>&1
goto :loop

:done
echo.
echo Monitor ended after !ITERATION! iterations.
endlocal
exit /b 0
