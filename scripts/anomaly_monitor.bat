@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM Windows Network Recovery Toolkit
REM Read-only anomaly monitor for TCP connection behavior.
REM --
REM Purpose: Detect growth/spike anomalies over recent samples (temp PowerShell helper file).
REM Side effects: Writes ephemeral PS under %TEMP% per run; deletes when complete.

title Windows Network Recovery Toolkit - Anomaly Detection Monitor

set "INTERVAL_SECONDS=2"
if not "%~1"=="" set "INTERVAL_SECONDS=%~1"
if defined MONITOR_INTERVAL_SECONDS set "INTERVAL_SECONDS=%MONITOR_INTERVAL_SECONDS%"
if not "%~2"=="" set "MAX_ITERATIONS=%~2"

set "ITERATION=0"
set "TW_HISTORY="
set "EST_HISTORY="
set "PS_FILE=%TEMP%\wnrt_anomaly_monitor_%RANDOM%%RANDOM%.ps1"

(
echo param^( [string]$TwHistoryCsv = '', [string]$EstHistoryCsv = '' ^)
echo $twHistory = @^(^)
echo if ^($TwHistoryCsv^) { $twHistory = $TwHistoryCsv -split ',' ^| Where-Object { $_ -match '^[0-9]+$' } ^| ForEach-Object { [int]$_ } }
echo $estHistory = @^(^)
echo if ^($EstHistoryCsv^) { $estHistory = $EstHistoryCsv -split ',' ^| Where-Object { $_ -match '^[0-9]+$' } ^| ForEach-Object { [int]$_ } }
echo $twRapid = $false
echo $twSpike = $false
echo if ^($twHistory.Count -ge 2^) {
echo   $prev = $twHistory[-2]
echo   $cur = $twHistory[-1]
echo   if ^($prev -gt 0 -and $cur -gt ^($prev * 2^)^) { $twRapid = $true }
echo   if ^(($cur - $prev^) -gt 1000^) { $twSpike = $true }
echo }
echo $twContinuous = $false
echo if ^($twHistory.Count -ge 5^) {
echo   $last5 = $twHistory[-5..-1]
echo   $inc = $true
echo   for ^($i = 1; $i -lt $last5.Count; $i++^) { if ^($last5[$i] -le $last5[$i-1]^) { $inc = $false; break } }
echo   $twContinuous = $inc
echo }
echo $estRapid = $false
echo $estSpike = $false
echo if ^($estHistory.Count -ge 2^) {
echo   $prev = $estHistory[-2]
echo   $cur = $estHistory[-1]
echo   if ^($prev -gt 0 -and $cur -gt ^($prev * 2^)^) { $estRapid = $true }
echo   if ^(($cur - $prev^) -gt 1000^) { $estSpike = $true }
echo }
echo $estContinuous = $false
echo if ^($estHistory.Count -ge 5^) {
echo   $last5 = $estHistory[-5..-1]
echo   $inc = $true
echo   for ^($i = 1; $i -lt $last5.Count; $i++^) { if ^($last5[$i] -le $last5[$i-1]^) { $inc = $false; break } }
echo   $estContinuous = $inc
echo }
echo $anomaly = $twRapid -or $twSpike -or $twContinuous -or $estRapid -or $estSpike -or $estContinuous
echo $status = if ^($anomaly^) { '[WARN] Abnormal growth detected' } else { 'Stable trend' }
echo $why = if ^($twRapid -or $twSpike -or $twContinuous^) { 'Possible connection leak or uncontrolled request loop ^(TIME_WAIT behavior^).' } elseif ^($estRapid -or $estSpike -or $estContinuous^) { 'Possible uncontrolled persistent connection growth ^(ESTABLISHED behavior^).' } else { 'No anomaly pattern in current sliding window.' }
echo "TW_HISTORY=$($twHistory -join ',')"
echo "EST_HISTORY=$($estHistory -join ',')"
echo "TW_SERIES=$($twHistory -join ' -> ')"
echo "EST_SERIES=$($estHistory -join ' -> ')"
echo "TW_RAPID=$($twRapid.ToString().ToUpper())"
echo "TW_CONTINUOUS=$($twContinuous.ToString().ToUpper())"
echo "TW_SPIKE=$($twSpike.ToString().ToUpper())"
echo "EST_RAPID=$($estRapid.ToString().ToUpper())"
echo "EST_CONTINUOUS=$($estContinuous.ToString().ToUpper())"
echo "EST_SPIKE=$($estSpike.ToString().ToUpper())"
echo "ANOMALY=$($anomaly.ToString().ToUpper())"
echo "STATUS=$status"
echo "WHY=$why"
) > "%PS_FILE%"

:loop
set /a ITERATION+=1

for /f %%A in ('netstat -an ^| find "TIME_WAIT" /c') do set "CUR_TIME_WAIT=%%A"
for /f %%A in ('netstat -an ^| find "ESTABLISHED" /c') do set "CUR_ESTABLISHED=%%A"

if defined TW_HISTORY (
    set "TW_HISTORY=!TW_HISTORY!,!CUR_TIME_WAIT!"
) else (
    set "TW_HISTORY=!CUR_TIME_WAIT!"
)
if defined EST_HISTORY (
    set "EST_HISTORY=!EST_HISTORY!,!CUR_ESTABLISHED!"
) else (
    set "EST_HISTORY=!CUR_ESTABLISHED!"
)

for /f %%A in ('powershell -NoProfile -ExecutionPolicy Bypass -Command "$a = '!TW_HISTORY!' -split ',' ^| Where-Object { $_ -match '^[0-9]+$' }; if($a.Count -gt 10){$a=$a[-10..-1]}; $a -join ','"') do set "TW_HISTORY=%%A"
for /f %%A in ('powershell -NoProfile -ExecutionPolicy Bypass -Command "$a = '!EST_HISTORY!' -split ',' ^| Where-Object { $_ -match '^[0-9]+$' }; if($a.Count -gt 10){$a=$a[-10..-1]}; $a -join ','"') do set "EST_HISTORY=%%A"

for /f "tokens=1,* delims==" %%A in ('powershell -NoProfile -ExecutionPolicy Bypass -File "%PS_FILE%" -TwHistoryCsv "!TW_HISTORY!" -EstHistoryCsv "!EST_HISTORY!"') do (
    set "%%A=%%B"
)

for /f %%A in ('powershell -NoProfile -Command "Get-Date -Format \"yyyy-MM-dd HH:mm:ss\""') do set "NOW_TS=%%A"

cls
echo ==========================================
echo Anomaly Detection Monitor
echo ==========================================
echo Timestamp: !NOW_TS!   ^|   Interval: !INTERVAL_SECONDS!s   ^|   Iteration: !ITERATION!
echo.
echo TIME_WAIT:
echo !TW_SERIES!
echo.
echo ESTABLISHED:
echo !EST_SERIES!
echo.
echo Status:
echo !STATUS!
echo.
echo Interpretation:
echo !WHY!
echo.
echo Signals:
echo - TIME_WAIT rapid growth: !TW_RAPID!
echo - TIME_WAIT continuous growth ^(5 cycles^): !TW_CONTINUOUS!
echo - TIME_WAIT sudden spike ^(delta ^> 1000^): !TW_SPIKE!
echo - ESTABLISHED rapid growth: !EST_RAPID!
echo - ESTABLISHED continuous growth ^(5 cycles^): !EST_CONTINUOUS!
echo - ESTABLISHED sudden spike ^(delta ^> 1000^): !EST_SPIKE!
echo.
echo ------------------------------------------
echo Press Ctrl+C to exit.
echo ------------------------------------------

if defined MAX_ITERATIONS (
    if !ITERATION! GEQ !MAX_ITERATIONS! goto :done
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Sleep -Seconds !INTERVAL_SECONDS!" >nul 2>&1
goto :loop

:done
echo.
echo Monitor ended after !ITERATION! iterations.
if exist "%PS_FILE%" del "%PS_FILE%" >nul 2>&1
endlocal
exit /b 0
