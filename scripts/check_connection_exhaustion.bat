@echo off
setlocal EnableExtensions

REM Windows Network Recovery Toolkit
REM Read-only diagnostic script for possible TCP connection exhaustion.
REM --
REM Purpose: Summarize TIME_WAIT/ESTABLISHED signals and suggest next steps (no net changes).
REM Privileges: Standard user unless netstat/tasklist require elevation in policy.

title Windows Network Recovery Toolkit - Connection Exhaustion Diagnosis

set "TIME_WAIT_COUNT=0"
set "ESTABLISHED_COUNT=0"
set "TIME_WAIT_LEVEL=Unknown"
set "TIME_WAIT_NOTE=Unable to interpret TIME_WAIT count."
set "ESTABLISHED_LEVEL=Review"
set "ESTABLISHED_NOTE=Review active connections and the top process list below."
set "DIAGNOSIS=No obvious connection exhaustion detected."

echo ==========================================
echo Connection Exhaustion Diagnosis
echo ==========================================
echo.
echo This script is read-only. It does not change Windows network settings.
echo It looks for signs of socket leaks or ephemeral port exhaustion.
echo.

echo [1] TIME_WAIT connections
echo ------------------------------------------
for /f %%A in ('netstat -an ^| find "TIME_WAIT" /c') do set "TIME_WAIT_COUNT=%%A"
echo Raw command: netstat -an ^| find "TIME_WAIT" /c
echo TIME_WAIT connections: %TIME_WAIT_COUNT%

if %TIME_WAIT_COUNT% LSS 1000 (
    set "TIME_WAIT_LEVEL=Normal"
    set "TIME_WAIT_NOTE=Normal. This is usually expected on an active system."
) else if %TIME_WAIT_COUNT% LEQ 5000 (
    set "TIME_WAIT_LEVEL=High usage"
    set "TIME_WAIT_NOTE=High usage. This may be normal for heavy API, browser, or developer workloads."
) else (
    set "TIME_WAIT_LEVEL=Possible connection leak"
    set "TIME_WAIT_NOTE=High. This may indicate socket leak behavior or ports being consumed too quickly."
    set "DIAGNOSIS=Possible connection exhaustion detected."
)

echo Interpretation: %TIME_WAIT_LEVEL%
echo %TIME_WAIT_NOTE%
echo.

echo [2] ESTABLISHED connections
echo ------------------------------------------
for /f %%A in ('netstat -an ^| find "ESTABLISHED" /c') do set "ESTABLISHED_COUNT=%%A"
echo Raw command: netstat -an ^| find "ESTABLISHED" /c
echo ESTABLISHED connections: %ESTABLISHED_COUNT%

if %ESTABLISHED_COUNT% LSS 500 (
    set "ESTABLISHED_LEVEL=Normal"
    set "ESTABLISHED_NOTE=Normal for most desktop systems."
) else if %ESTABLISHED_COUNT% LEQ 2000 (
    set "ESTABLISHED_LEVEL=High usage"
    set "ESTABLISHED_NOTE=High. Check the top TCP process list for browsers, API clients, bots, or WebSocket-heavy apps."
) else (
    set "ESTABLISHED_LEVEL=Very high"
    set "ESTABLISHED_NOTE=Very high. Persistent connections may be consuming network resources."
    set "DIAGNOSIS=Possible connection exhaustion or unusually heavy persistent connection usage detected."
)

echo Interpretation: %ESTABLISHED_LEVEL%
echo %ESTABLISHED_NOTE%
echo.

echo [3] Top TCP processes
echo ------------------------------------------
echo Raw source: Get-NetTCPConnection grouped by OwningProcess
echo.
echo PID    Process Name                 Connection Count
echo -----  ---------------------------  ----------------
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-NetTCPConnection | Group-Object OwningProcess | Sort-Object Count -Descending | Select-Object -First 15 @{Name='PID';Expression={[int]$_.Name}}, @{Name='ProcessName';Expression={try { (Get-Process -Id ([int]$_.Name) -ErrorAction Stop).ProcessName } catch { 'Unknown' }}}, @{Name='Connections';Expression={$_.Count}} | ForEach-Object { '{0,-5}  {1,-27}  {2,16}' -f $_.PID, $_.ProcessName, $_.Connections }"
echo.
echo Interpretation:
echo - A single process with thousands of connections may be leaking sockets.
echo - Common sources include scripts, API clients, browsers, sync tools, Docker, WSL, or test runners.
echo - If a process name is Unknown, Windows did not expose the process name to this read-only check.
echo.

echo [4] Ephemeral port range
echo ------------------------------------------
echo Raw command: netsh int ipv4 show dynamicport tcp
netsh int ipv4 show dynamicport tcp
echo.
echo Parsed view:
powershell -NoProfile -ExecutionPolicy Bypass -Command "$out = netsh int ipv4 show dynamicport tcp; $start = ($out | Select-String 'Start Port\s*:\s*(\d+)').Matches.Groups[1].Value; $count = ($out | Select-String 'Number of Ports\s*:\s*(\d+)').Matches.Groups[1].Value; if ($start -and $count) { 'Start Port: ' + $start; 'Number of Ports: ' + $count } else { 'Unable to parse dynamic port range from localized netsh output.' }"
echo.
echo Interpretation:
echo - Windows uses ephemeral ports for outbound TCP connections.
echo - Exhaustion risk increases when applications create many short-lived connections quickly.
echo - A large TIME_WAIT count can mean ports are being consumed faster than they are released.
echo.

echo ------------------------------------------
echo Diagnosis:
echo %DIAGNOSIS%
echo.

if "%DIAGNOSIS%"=="No obvious connection exhaustion detected." (
    echo Suggested actions:
    echo - If only one browser fails, try another browser or reset browser settings.
    echo - If failures happen after long uptime, run this script again while the issue is active.
    echo - Continue with auto_diagnose.bat for DNS, proxy, TCP, and HTTPS checks.
) else (
    echo Common causes:
    echo - Python requests loop without connection reuse
    echo - WebSocket or API polling without closing connections
    echo - Bots, scrapers, or test tools opening many connections
    echo - Docker / WSL / Hyper-V networking issues
    echo - Browser extensions or sync tools creating many persistent connections
    echo.
    echo Suggested actions:
    echo - Restart the application using the network heavily.
    echo - Check code for connection reuse, such as requests.Session in Python.
    echo - Reduce aggressive polling or retry loops.
    echo - Restart Windows to reset the socket pool if the machine is currently stuck.
    echo - Re-run this script after restart to compare counts.
)

echo ------------------------------------------
echo.
echo This script did not change any settings.
echo.

pause
endlocal
