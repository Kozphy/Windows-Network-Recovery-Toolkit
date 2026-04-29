@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM Windows Network Recovery Toolkit
REM Read-only real-time TCP connection monitor.

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

if "%WARN_SPIKE%"=="YES" (
    set "STATUS=[WARN] Connection spike detected"
    set "STATUS_LINE=TIME_WAIT increased rapidly."
    set "CAUSE_1=API polling loop or retry storm."
    set "CAUSE_2=WebSocket flood or connection churn."
    set "CAUSE_3=Unclosed connections in application code."
)

if "%WARN_GROWTH%"=="YES" (
    set "STATUS=[WARN] Abnormal TIME_WAIT growth"
    set "STATUS_LINE=TIME_WAIT rose sharply relative to the previous sample."
    set "CAUSE_1=Potential socket leak behavior."
    set "CAUSE_2=Excessive short-lived outbound connections."
    set "CAUSE_3=Ephemeral ports may be consumed too quickly."
)

if "%WARN_DOMINANT%"=="YES" (
    set "STATUS=[WARN] Single process dominates TCP usage"
    set "STATUS_LINE=%TOP_NAME% (PID %TOP_PID%) currently owns most active connections."
    set "CAUSE_1=A single app may be saturating network sessions."
    set "CAUSE_2=Inspect app retry logic, pooling, and connection lifecycle."
    set "CAUSE_3=Stop or restart the process for a quick A/B check."
)

if "%WARN_TOP_INCREASING%"=="YES" (
    set "STATUS=[WARN] Dominant process is still increasing"
    set "STATUS_LINE=%TOP_NAME% connection count is rising quickly."
    set "CAUSE_1=Persistent growth pattern can precede exhaustion."
    set "CAUSE_2=Check application logs for repeated outbound attempts."
    set "CAUSE_3=Consider restarting the process and monitoring trend reset."
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
